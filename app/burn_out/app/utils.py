import asyncio
import time
from trame.app import asynchronous


def create_throttler(interval):
    """
    Returns a throttled_call function that:
    1. Runs immediately on first call or after throttle interval
    2. Ensures the last request always gets executed after throttle time
    3. Supports both sync and async functions

    Args:
        interval: Minimum time between function executions in seconds

    Returns:
        async function that accepts either a sync or async function to throttle
    """
    # State held in closure
    last_run_time = 0
    pending_task = None
    has_pending_request = False

    async def _delayed_call(func, delay):
        nonlocal last_run_time, has_pending_request
        await asyncio.sleep(delay)
        if has_pending_request:  # Only run if there's still a pending request
            last_run_time = time.time()
            has_pending_request = False
            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                func()

    async def throttled_call(func):
        nonlocal last_run_time, pending_task, has_pending_request

        current_time = time.time()
        time_since_last_run = current_time - last_run_time

        if time_since_last_run >= interval:
            # Run immediately - first call or enough time has passed
            last_run_time = current_time
            has_pending_request = False
            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                func()
        else:
            # Schedule for later and mark that we have a pending request
            has_pending_request = True
            if pending_task is None or pending_task.done():
                delay = interval - time_since_last_run
                pending_task = asynchronous.create_task(_delayed_call(func, delay))

    return throttled_call


async def wait_for_network_and_time(server, target_duration):
    """
    Waits for the server to complete network operations and then sleeps
    for the remaining time to match the target duration.
    """
    start_time = asyncio.get_event_loop().time()
    await server.network_completion
    network_time = asyncio.get_event_loop().time() - start_time

    remaining_time = target_duration - network_time

    if remaining_time > 0:
        await asyncio.sleep(remaining_time)


class VideoAdapter:
    def __init__(self, name, on_streamer_set=None):
        self.area_name = name
        self.streamer = None
        self.meta = None
        self.on_streamer_set = (
            on_streamer_set  # Callback to be called when streamer is set
        )

    def set_streamer(self, stream_manager):
        self.streamer = stream_manager
        if self.on_streamer_set:
            self.on_streamer_set()

    def clear(self):
        self.meta = None

    def update_frame(self, kwiver_image):
        if self.meta is None:
            self.meta = dict(
                type="image/rgb24",
                w=int(kwiver_image.width()),
                h=int(kwiver_image.height()),
            )
        self.streamer.push_content(
            self.area_name, self.meta, memoryview(kwiver_image.asarray().ravel())
        )
