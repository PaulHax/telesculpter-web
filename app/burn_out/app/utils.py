class VideoAdapter:
    def __init__(self, name):
        self.area_name = name
        self.streamer = None
        self.meta = None

    def set_streamer(self, stream_manager):
        self.streamer = stream_manager

    def update_frame(self, kwiver_image):
        # if we open a new video this needs to be updated. force update every time for now
        # if self.meta is None:
        meta = dict(
            type="image/rgb24",
            w=int(kwiver_image.width()),
            h=int(kwiver_image.height()),
        )
        if meta != self.meta:
            self.meta = meta
        self.streamer.push_content(
            self.area_name, self.meta, memoryview(kwiver_image.asarray().ravel())
        )
