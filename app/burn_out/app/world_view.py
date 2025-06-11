from typing import NamedTuple, Sequence

from vtkmodules.vtkCommonDataModel import (
    vtkPolyData,
    vtkCellArray,
    vtkPlanes,
)
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkRenderer,
    vtkRenderWindow,
)
from vtkmodules.vtkFiltersSources import vtkFrustumSource
from vtkmodules.vtkFiltersCore import vtkAppendPolyData

from trame.decorators import TrameApp
from trame.widgets import vtk as vtk_widgets

colors = vtkNamedColors()


class Positions_Rep(NamedTuple):
    poly_data: vtkPolyData
    mapper: vtkPolyDataMapper
    actor: vtkActor


class Frustums_Rep(NamedTuple):
    poly_data: vtkPolyData  # Holds the combined output of append_poly_data
    mapper: vtkPolyDataMapper
    actor: vtkActor
    append_poly_data: vtkAppendPolyData  # Filter to combine individual frustums
    dummy_input_poly_data: vtkPolyData  # Added: A persistent empty polydata


class Pipeline(NamedTuple):
    positions_rep: Positions_Rep
    frustums_rep: Frustums_Rep  # Added
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
    actor.GetProperty().SetColor(colors.GetColor3d("Cyan"))
    renderer.AddActor(actor)

    return Positions_Rep(
        poly_data=poly_data,
        mapper=mapper,
        actor=actor,
    )


def create_frustums_rep(renderer: vtkRenderer):
    output_poly_data = vtkPolyData()
    append_filter = vtkAppendPolyData()
    dummy_pd = vtkPolyData()
    append_filter.AddInputData(dummy_pd)

    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(append_filter.GetOutputPort())

    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(colors.GetColor3d("Red"))
    actor.GetProperty().SetRepresentationToWireframe()

    renderer.AddActor(actor)

    return Frustums_Rep(
        poly_data=output_poly_data,
        mapper=mapper,
        actor=actor,
        append_poly_data=append_filter,
        dummy_input_poly_data=dummy_pd,
    )


def update_frustums_rep(
    frustums_rep: Frustums_Rep, camera_map_serialized, display_density: int = 1
):
    if display_density < 1:
        display_density = 1

    frustums_rep.append_poly_data.RemoveAllInputs()

    any_frustum_added = False
    cameras = list(camera_map_serialized.values())

    for i in range(0, len(cameras), display_density):
        camera_data = cameras[i]
        planes_coefficients = camera_data.get("planes")
        # Expecting 24 float coefficients for the 6 frustum planes
        if planes_coefficients and len(planes_coefficients) == 24:
            planes_object = vtkPlanes()
            planes_object.SetFrustumPlanes(planes_coefficients)

            frustum_source = vtkFrustumSource()
            frustum_source.SetPlanes(planes_object)
            frustum_source.ShowLinesOff()
            frustum_source.Update()

            # DeepCopy the output to ensure each frustum is a distinct dataset
            individual_frustum_poly_data = vtkPolyData()
            individual_frustum_poly_data.DeepCopy(frustum_source.GetOutput())

            frustums_rep.append_poly_data.AddInputData(individual_frustum_poly_data)
            any_frustum_added = True

    if not any_frustum_added:
        frustums_rep.append_poly_data.AddInputData(frustums_rep.dummy_input_poly_data)

    frustums_rep.append_poly_data.Update()
    frustums_rep.poly_data.ShallowCopy(frustums_rep.append_poly_data.GetOutput())

    frustums_rep.poly_data.Modified()


def create_pipeline():
    renderer = vtkRenderer()
    renderer.ResetCamera()
    renderer.SetBackground(0, 0, 0)

    render_window = vtkRenderWindow()
    render_window.AddRenderer(renderer)

    return Pipeline(
        positions_rep=create_camera_position_rep(renderer),
        frustums_rep=create_frustums_rep(renderer),
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

    def update_camera_map(self, camera_map):
        point_data = [camera["center"] for camera in camera_map.values()]

        update_positions_rep(self.pipeline.positions_rep, point_data)
        update_frustums_rep(self.pipeline.frustums_rep, camera_map, 340)

        self.pipeline.renderer.ResetCamera()
        self.html_view.push_camera()
        self.html_view.update()
