import logging
import multiprocessing as mp
import os
import threading
import uuid


class JobWorker:
    """
    Encapsulate a multiprocessing process.
    """
    def __init__(self, job_queue, result_queue):
        self._logger = logging.getLogger(f"Worker-{os.getpid()}")
        self._job_queue = job_queue
        self._result_queue = result_queue

    def start(self):
        p = mp.Process(target=self._process_entry)
        p.start()

    def _process_entry(self):
        while True:
            job = self._job_queue.get()
            self._logger.debug("Got job %s", job["id"])
            self._handle_job(job)

    def _handle_job(self, job):
        func = job["func"]
        kwargs = job["kwargs"]
        ret_value = func(**kwargs)
        job_result = dict(
            worker_pid=os.getpid(), job_id=job["id"], return_value=ret_value
        )
        self._result_queue.put(job_result)


class JobManager:
    def __init__(self, number_of_workers: int = 4):
        self._logger = logging.getLogger("JobManager")
        self._job_queue = mp.Queue()
        self._result_queue = mp.Queue()
        self._job_id_to_callback_map = dict()

        self._start_result_monitoring_thread()
        self._start_worker_processes(number_of_workers)

    def _start_result_monitoring_thread(self):
        thread = threading.Thread(target=self._result_monitor_thread_entry)
        thread.daemon = True
        thread.start()

    def _start_worker_processes(self, num_workers: int) -> None:
        for i in range(num_workers):
            worker = JobWorker(self._job_queue, self._result_queue)
            worker.start()

    def _result_monitor_thread_entry(self) -> None:
        while True:
            job_result = self._result_queue.get()

            job_id = job_result["job_id"]
            return_value = job_result["return_value"]
            try:
                self._run_callback(job_id, return_value)
            except Exception:
                self._logger.exception("Failed to run callback")

    def _run_callback(self, job_id, return_value):
        callback_details = self._job_id_to_callback_map.pop(job_id, None)
        if not callback_details:
            self._logger.error("Didn't find the callback for %s", job_id)
            return

        callback_func = callback_details["func"]
        callback_kwargs = callback_details["kwargs"]
        callback_func(return_value, **callback_kwargs)

    def enqueue_job(
        self, *, job_func, job_func_kwargs, callback_func, callback_func_kwargs
    ) -> None:
        job_id = uuid.uuid4()
        job_description = {
            "id": job_id,
            "func": job_func,
            "kwargs": job_func_kwargs,
        }
        self._job_id_to_callback_map[job_id] = {
            "func": callback_func,
            "kwargs": callback_func_kwargs
        }
        self._job_queue.put(job_description)
