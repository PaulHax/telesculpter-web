"""Functional multiprocess utility for long-running tasks in async applications.

This provides pure functions for managing worker processes with proper Ctrl+C handling.
"""

import asyncio
from multiprocessing import Process, Queue
from typing import Any, Callable, NamedTuple, Optional, Tuple


class WorkerHandle(NamedTuple):
    """Immutable worker process handle."""

    worker_func: Callable[[Queue, Queue], None]
    task_queue: Queue
    result_queue: Queue
    process: Process


def create_worker(worker_func: Callable[[Queue, Queue], None]) -> WorkerHandle:
    """Create a new worker process.

    Args:
        worker_func: Function that runs in worker process.
                    Must accept (task_queue, result_queue) as arguments.

    Returns:
        WorkerHandle for the created worker
    """
    task_queue = Queue()
    result_queue = Queue()
    process = Process(target=worker_func, args=(task_queue, result_queue), daemon=True)
    process.start()

    return WorkerHandle(worker_func, task_queue, result_queue, process)


def send_task(worker: WorkerHandle, task: Any) -> WorkerHandle:
    """Send task to worker process.

    Args:
        worker: Worker handle
        task: Task to send

    Returns:
        Worker handle (same if alive, new if restarted)
    """
    # Restart if process is dead
    if not worker.process.is_alive():
        worker = create_worker(worker.worker_func)

    worker.task_queue.put(task)
    return worker


async def await_result(
    worker: WorkerHandle, timeout: Optional[float] = None
) -> Tuple[WorkerHandle, Optional[Any]]:
    """Wait for result from worker process.

    This function monitors the worker process and returns None if the process
    dies (e.g., from Ctrl+C) instead of hanging forever.

    Args:
        worker: Worker handle
        timeout: Optional timeout in seconds (default: wait forever)

    Returns:
        Tuple of (worker_handle, result). Result is None if process died.
    """
    loop = asyncio.get_event_loop()
    start_time = asyncio.get_event_loop().time() if timeout is not None else None

    # Monitor process health while waiting for results
    while worker.process.is_alive():
        try:
            result = await loop.run_in_executor(
                None,
                worker.result_queue.get,
                True,
                0.1,  # Short queue timeout
            )
            return worker, result
        except Exception:
            if timeout is not None and start_time is not None:
                if asyncio.get_event_loop().time() - start_time > timeout:
                    return worker, None
            continue

    # Process died without sending results
    return worker, None


async def send_and_await(
    worker: WorkerHandle, task: Any, timeout: Optional[float] = None
) -> Tuple[WorkerHandle, Optional[Any]]:
    """Send task and await result in one operation.

    Args:
        worker: Worker handle
        task: Task to send
        timeout: Optional timeout in seconds (default: wait forever)

    Returns:
        Tuple of (worker_handle, result)
    """
    worker = send_task(worker, task)
    return await await_result(worker, timeout)


def close_worker(worker: WorkerHandle) -> None:
    """Close worker process gracefully.

    Args:
        worker: Worker handle to close
    """
    if worker.process.is_alive():
        worker.task_queue.put(None)  # Signal shutdown
        worker.process.join(timeout=1.0)
        if worker.process.is_alive():
            worker.process.terminate()


def cancel_worker(worker: WorkerHandle) -> WorkerHandle:
    """Cancel current operations and restart worker.

    Args:
        worker: Worker handle to cancel

    Returns:
        New worker handle
    """
    if worker.process.is_alive():
        worker.process.terminate()
        worker.process.join(timeout=1.0)
        if worker.process.is_alive():
            worker.process.kill()

    return create_worker(worker.worker_func)


# Example worker functions


def simple_worker(task_queue: Queue, result_queue: Queue):
    """Simple worker that processes tasks until None is received."""
    for task in iter(task_queue.get, None):
        try:
            result = f"Processed: {task}"
            result_queue.put(result)
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            result_queue.put(f"Error: {e}")


# Functional usage example
async def demo_functional_style():
    """Demo functional programming style."""
    # Create worker
    worker = create_worker(simple_worker)

    try:
        # Send task and await result in one call
        worker, result1 = await send_and_await(worker, "Hello")
        print(f"Result 1: {result1}")

        # Or separate operations
        worker = send_task(worker, "World")
        worker, result2 = await await_result(worker)
        print(f"Result 2: {result2}")

    finally:
        close_worker(worker)


if __name__ == "__main__":
    import asyncio

    asyncio.run(demo_functional_style())
