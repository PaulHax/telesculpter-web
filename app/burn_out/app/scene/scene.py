from trame.decorators import TrameApp
from kwiver.vital.types import SFMConstraints


@TrameApp()
class Scene:
    def __init__(self, server):
        self.server = server

    def set_metadata(self, metadata):
        self.metadata = metadata
        self.sfm_constraints = SFMConstraints()
        self.sfm_constraints.metadata = metadata
