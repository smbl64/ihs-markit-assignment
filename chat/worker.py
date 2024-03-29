import logging
import multiprocessing as mp
import os
import threading
import uuid


DEFAULT_WORKER_COUNT = 4

class JobWorker:
    """
    Encapsulate a multiprocessing process.
    """

    def __init__(self, job_queue, result_queue):
        self._job_queue = job_queue
        self._result_queue = result_queue

    def start(self):
        p = mp.Process(target=self._process_entry)
        p.start()

    def _process_entry(self):
        self._logger = logging.getLogger(f"Worker-{os.getpid()}")
        while True:
            job = self._job_queue.get()
            self._handle_job(job)

    def _handle_job(self, job):
        job_id = job["id"]
        func = job["func"]
        kwargs = job["kwargs"]
        self._logger.debug("Got job %s. func=%s, kwargs=%s", job_id, func, kwargs)
        try:
            ret_value = func(**kwargs)
            self._logger.debug("Finished running the job %s", job_id)
        except Exception:
            self._logger.exception("Failed to run the job", job_id)
            return

        job_result = dict(worker_pid=os.getpid(), job_id=job_id, return_value=ret_value)
        self._result_queue.put(job_result)


class JobManager:
    """
    The main class for managing the job system and handling
    the worker processes.
    """
    def __init__(self, number_of_workers: int = DEFAULT_WORKER_COUNT):
        self._logger = logging.getLogger(self.__class__.__name__)
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
        """
        Enqueue a job to be run in the background.

        :param job_func: The function to call for the job.
        :param job_func_kwargs: An optional dictionary representing the kwargs for
            the job function.
        :param callback_func: The function to call when the job is finished.
        :param callback_func_kwargs: An optional dictionary of kwargs to send to the
            callback function.
        """
        if not job_func_kwargs:
            job_func_kwargs = dict()
        if not callback_func_kwargs:
            callback_func_kwargs = dict()

        job_id = uuid.uuid4()
        job_description = {
            "id": job_id,
            "func": job_func,
            "kwargs": job_func_kwargs,
        }
        self._job_id_to_callback_map[job_id] = {
            "func": callback_func,
            "kwargs": callback_func_kwargs,
        }
        self._job_queue.put(job_description)
