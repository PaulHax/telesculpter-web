import asyncio


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
