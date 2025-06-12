from typing import NamedTuple, Sequence
import numpy as np
from vtkmodules.vtkCommonDataModel import (
    vtkPolyData,
    vtkCellArray,
    vtkPlanes,
    vtkTriangle,
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

from .scene.utils import (
    get_frustum_planes_from_simple_camera,  # Added
)


colors = vtkNamedColors()

NEAR_CLIP = 0.01
FAR_CLIP = 4.0


def build_camera_frustum(
    planes_coefficients: Sequence[float], out_poly_data: vtkPolyData
):
    """
    Builds a camera frustum including an up-indicator triangle, similar to
    the C++ BuildCameraFrustum function.
    """
    planes_object = vtkPlanes()
    planes_object.SetFrustumPlanes(planes_coefficients)

    frustum_source = vtkFrustumSource()
    frustum_source.SetPlanes(planes_object)
    frustum_source.ShowLinesOff()  # Generates 5 faces (no lines) and 8 points
    frustum_source.Update()

    # Make a copy of the frustum mesh so we can modify it
    out_poly_data.DeepCopy(frustum_source.GetOutput())
    frustum_points = out_poly_data.GetPoints()
    frustum_polys = out_poly_data.GetPolys()

    if not frustum_points or frustum_points.GetNumberOfPoints() != 8:
        # Expected 8 points for the frustum (4 near, 4 far)
        return

    # Points from vtkFrustumSource (ShowLinesOff=True):
    # Far plane: 0:FBL, 1:FBR, 2:FTR, 3:FTL
    # Near plane: 4:NBL, 5:NBR, 6:NTR, 7:NTL

    p0_fbl = np.array(frustum_points.GetPoint(0))  # Far Bottom Left
    p1_fbr = np.array(frustum_points.GetPoint(1))  # Far Bottom Right
    p2_ftr = np.array(frustum_points.GetPoint(2))  # Far Top Right
    p3_ftl = np.array(frustum_points.GetPoint(3))  # Far Top Left

    # Calculate the center of the far face
    center_face = 0.25 * (p0_fbl + p1_fbr + p2_ftr + p3_ftl)

    # Calculate the new tip point for the up-indicator triangle
    # new = top_edge_midpoint + (top_edge_midpoint - center_face_midpoint_along_up_vector)
    # Simplified from C++: new = p2 + p3 - center
    # where p2 and p3 are the top corners of the far plane.
    tip_coord = p2_ftr + p3_ftl - center_face

    # Insert new point for the tip of the up-indicator
    tip_point_id = frustum_points.InsertNextPoint(
        tip_coord[0], tip_coord[1], tip_coord[2]
    )

    # Create the up-indicator triangle using the far plane's top edge points
    # and the new tip point.
    # The C++ code uses original indices 2 and 3 for the triangle.
    # Index 2 from frustum_source output is FTR.
    # Index 3 from frustum_source output is FTL.
    up_triangle = vtkTriangle()
    up_triangle.GetPointIds().SetId(0, 2)  # Far Top Right (original index 2)
    up_triangle.GetPointIds().SetId(1, 3)  # Far Top Left (original index 3)
    up_triangle.GetPointIds().SetId(2, tip_point_id)

    if frustum_polys is None:
        frustum_polys = vtkCellArray()
        out_poly_data.SetPolys(frustum_polys)

    frustum_polys.InsertNextCell(up_triangle)
    out_poly_data.Modified()


class Positions_Rep(NamedTuple):
    poly_data: vtkPolyData
    mapper: vtkPolyDataMapper
    actor: vtkActor


class Frustums_Rep(NamedTuple):
    poly_data: vtkPolyData  # Holds the combined output of append_poly_data
    mapper: vtkPolyDataMapper
    actor: vtkActor
    append_poly_data: vtkAppendPolyData
    dummy_input_poly_data: vtkPolyData


class Pipeline(NamedTuple):
    positions_rep: Positions_Rep
    frustums_rep: Frustums_Rep
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

    # workaround: initial actor needs renderable polydata or Color and SetRepresentationToWireframe won't work without full browser refresh
    points = vtkPoints()
    points.InsertNextPoint(0, 0, 0)
    points.InsertNextPoint(1, 0, 0)
    points.InsertNextPoint(0, 1, 0)
    dummy_pd.SetPoints(points)

    triangle = vtkTriangle()
    triangle.GetPointIds().SetId(0, 0)
    triangle.GetPointIds().SetId(1, 1)
    triangle.GetPointIds().SetId(2, 2)

    polys = vtkCellArray()
    polys.InsertNextCell(triangle)
    dummy_pd.SetPolys(polys)

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


def update_frustums_rep(frustums_rep: Frustums_Rep, frustums, display_density: int = 1):
    frustums_rep.append_poly_data.RemoveAllInputs()

    any_frustum_added = False

    for i, planes_coefficients in enumerate(frustums):
        if i % display_density != 0:
            continue

        individual_frustum_poly_data = vtkPolyData()
        build_camera_frustum(planes_coefficients, individual_frustum_poly_data)

        if individual_frustum_poly_data.GetNumberOfPoints() > 0:
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
        self.camera_map = camera_map
        self._update_cameras()

    def _update_cameras(self):
        camera_map = self.camera_map

        centers = [camera.center().tolist() for camera in camera_map.values()]
        update_positions_rep(self.pipeline.positions_rep, centers)

        frustums = (
            get_frustum_planes_from_simple_camera(cam, NEAR_CLIP, FAR_CLIP)
            for cam in camera_map.values()
        )

        update_frustums_rep(self.pipeline.frustums_rep, frustums, 400)

        self.pipeline.renderer.ResetCamera()
        self.html_view.push_camera()
        self.html_view.update()
