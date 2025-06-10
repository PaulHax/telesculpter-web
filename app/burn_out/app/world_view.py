from typing import NamedTuple, Sequence

from vtkmodules.vtkCommonDataModel import vtkPolyData, vtkCellArray
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
)

from trame.decorators import TrameApp
from trame.widgets import vtk as vtk_widgets


class Positions_Rep(NamedTuple):
    poly_data: vtkPolyData
    mapper: vtkPolyDataMapper
    actor: vtkActor


class Pipeline(NamedTuple):
    positions_rep: Positions_Rep
    renderer: vtkRenderer
    render_window: vtkRenderWindow


def update_points(points: vtkPoints, lines: vtkCellArray, point_data: Sequence[float]):
    point_ids = []
    for point in point_data:
        point_id = points.InsertNextPoint(point[0], point[1], point[2])
        point_ids.append(point_id)

    lines.InsertNextCell(len(point_ids))
    for point_id in point_ids:
        lines.InsertCellPoint(point_id)


def update_positions_rep(positions_rep: Positions_Rep, point_data: Sequence[float]):
    points = vtkPoints()
    lines = vtkCellArray()
    update_points(
        points,
        lines,
        point_data,
    )
    positions_rep.poly_data.SetPoints(points)
    positions_rep.poly_data.SetLines(lines)
    positions_rep.poly_data.Modified()


def create_camera_position_rep(renderer: vtkRenderer):
    points = vtkPoints()
    lines = vtkCellArray()

    update_points(points, lines, [])

    poly_data = vtkPolyData()
    poly_data.SetPoints(points)
    poly_data.SetLines(lines)

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(poly_data)

    actor = vtkActor()
    actor.SetMapper(mapper)
    colors = vtkNamedColors()
    actor.GetProperty().SetColor(colors.GetColor3d("Red"))
    renderer.AddActor(actor)

    return Positions_Rep(
        poly_data=poly_data,
        mapper=mapper,
        actor=actor,
    )


def create_pipeline():
    renderer = vtkRenderer()
    renderer.ResetCamera()
    renderer.SetBackground(0, 0, 0)

    render_window = vtkRenderWindow()
    render_window.AddRenderer(renderer)

    return Pipeline(
        positions_rep=create_camera_position_rep(renderer),
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
        self.html_view.reset_camera()
        self.server.controller.on_server_ready.add(self.html_view.update)
        self.server.controller.reset_world_camera = self.html_view.reset_camera

    def update_camera_map(self, camera_map):
        point_data = [camera["center"] for camera in camera_map.values()]

        update_positions_rep(self.pipeline.positions_rep, point_data)

        self.pipeline.renderer.ResetCamera()
        self.html_view.push_camera()
        self.html_view.update()
