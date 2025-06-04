import asyncio
from typing import NamedTuple

from vtkmodules.vtkFiltersSources import vtkConeSource
from vtkmodules.vtkFiltersCore import vtkGlyph3D
from vtkmodules.vtkCommonDataModel import vtkPolyData
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
)

from trame.decorators import TrameApp
from trame.app import asynchronous
from trame.widgets import vtk as vtk_widgets


class Pipeline(NamedTuple):
    points: vtkPoints
    poly_data: vtkPolyData
    cone_source: vtkConeSource
    glyph3d: vtkGlyph3D
    mapper: vtkPolyDataMapper
    actor: vtkActor
    renderer: vtkRenderer
    render_window: vtkRenderWindow


def create_pipeline():
    points = vtkPoints()
    points.InsertNextPoint(1, 0, 0)

    poly_data = vtkPolyData()
    poly_data.SetPoints(points)

    cone_source = vtkConeSource()
    cone_source.SetResolution(2)
    cone_source.SetHeight(0.0005)
    cone_source.SetRadius(0.0002)

    glyph3d = vtkGlyph3D()  # Note: original code assigned this to self.glyph2D
    glyph3d.SetSourceConnection(cone_source.GetOutputPort())
    glyph3d.SetInputData(poly_data)
    glyph3d.Update()

    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(glyph3d.GetOutputPort())

    actor = vtkActor()
    actor.SetMapper(mapper)
    colors = vtkNamedColors()
    actor.GetProperty().SetColor(colors.GetColor3d("Red"))

    renderer = vtkRenderer()
    renderer.AddActor(actor)
    renderer.ResetCamera()
    renderer.SetBackground(0.1, 0.2, 0.3)

    render_window = vtkRenderWindow()
    render_window.AddRenderer(renderer)

    return Pipeline(
        points=points,
        poly_data=poly_data,
        cone_source=cone_source,
        glyph3d=glyph3d,
        mapper=mapper,
        actor=actor,
        renderer=renderer,
        render_window=render_window,
    )


@TrameApp()
class WorldView:
    def __init__(self, server):
        self.server = server
        self.server.controller.update_camera_map.add(self.update_camera_map)
        self.pipeline = create_pipeline()

    def create_view(self):
        self.html_view = vtk_widgets.VtkLocalView(
            self.pipeline.render_window, box_selection=False
        )
        self.server.controller.on_server_ready.add(self.html_view.update)
        self.server.controller.reset_world_camera = self.html_view.reset_camera

    async def _update_camera_map(self):
        print("Camera Map Updated")
        camera_map = self.server.context.camera_map

        points = vtkPoints()
        for frame_id, camera in camera_map.items():
            center = camera["center"]
            points.InsertNextPoint(center[0], center[1], center[2])
        self.pipeline.poly_data.SetPoints(points)
        self.pipeline.poly_data.Modified()

        with self.server.state:
            self.html_view.update()
        await self.server.network_completion
        await asyncio.sleep(0.1)  # hax
        self.html_view.reset_camera()
        print("Camera reset after delay")

    def update_camera_map(self):
        asynchronous.create_task(self._update_camera_map())
