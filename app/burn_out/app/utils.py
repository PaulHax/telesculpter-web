class VideoAdapter:
    def __init__(self, name):
        self.area_name = name
        self.streamer = None
        self.meta = None

    def set_streamer(self, stream_manager):
        self.streamer = stream_manager

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
