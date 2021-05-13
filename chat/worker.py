import multiprocessing as mp
import os
import threading
import uuid


def proc_func(job_queue: mp.Queue, result_queue: mp.Queue):
    while True:
        job = job_queue.get()
        print(f"{os.getpid()}: got job {job['id']}")
        func = job["func"]
        kwargs = job["kwargs"]
        ret_value = func(**kwargs)
        job_result = dict(
            worker_pid=os.getpid(), job_id=job["id"], return_value=ret_value
        )
        result_queue.put(job_result)


class JobManager:
    def __init__(self, number_of_workers: int = 4):
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
            p = mp.Process(target=proc_func, args=(self._job_queue, self._result_queue))
            p.start()

    def _result_monitor_thread_entry(self) -> None:
        while True:
            job_result = self._result_queue.get()

            job_id = job_result["job_id"]
            callback_details = self._job_id_to_callback_map.get(job_id, None)
            if not callback_details:
                print("Didn't find the callback!!")
                continue

            callback_func = callback_details["func"]
            callback_kwargs = callback_details["kwargs"]
            return_value = job_result["return_value"]
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


def start():
    import helpers
    manager = JobManager()

    def my_callback(*args):
        print("in callback --->", *args)

    for x in range(5, 15):
        manager.enqueue_job(
            job_func=helpers.fibonacci, callback_func=my_callback, params={"n": x}
        )


if __name__ == "__main__":
    start()
