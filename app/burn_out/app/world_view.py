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

from burn_out.app.scene.utils import get_frustum_planes


colors = vtkNamedColors()

NEAR_CLIP = 0.000001
FAR_CLIP = 0.001


class Positions_Rep(NamedTuple):
    poly_data: vtkPolyData
    mapper: vtkPolyDataMapper
    actor: vtkActor


class Frustums_Rep(NamedTuple):
    poly_data: vtkPolyData  # Holds the combined output of append_poly_data
    mapper: vtkPolyDataMapper
    actor: vtkActor
    append_poly_data: vtkAppendPolyData  # Filter to combine individual frustums
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


def update_frustums_rep(
    frustums_rep: Frustums_Rep, frustums_generator, display_density: int = 1
):
    frustums_rep.append_poly_data.RemoveAllInputs()

    any_frustum_added = False

    for i, planes_coefficients in enumerate(frustums_generator):
        if i % display_density != 0:
            continue

        # Expecting 24 float coefficients for the 6 frustum planes
        if planes_coefficients and len(planes_coefficients) == 24:
            planes_object = vtkPlanes()
            planes_object.SetFrustumPlanes(planes_coefficients)

            frustum_source = vtkFrustumSource()
            frustum_source.SetPlanes(planes_object)
            frustum_source.ShowLinesOff()
            frustum_source.Update()

            individual_frustum_poly_data = vtkPolyData()
            individual_frustum_poly_data.DeepCopy(frustum_source.GetOutput())

            frustum_points = individual_frustum_poly_data.GetPoints()
            if frustum_points and frustum_points.GetNumberOfPoints() == 8:
                # Use Far Plane points instead of Near Plane points
                pt_ftl_coords = np.array(frustum_points.GetPoint(3))  # Far Top Left
                pt_ftr_coords = np.array(frustum_points.GetPoint(2))  # Far Top Right
                pt_fbl_coords = np.array(frustum_points.GetPoint(0))  # Far Bottom Left

                # Geometric 'up' direction from Far Plane's vertical edge (FTL - FBL)
                # This mimics the C++ approach (which used near plane) but adapted for the far plane.
                # Quaternion-based calculation for 'up' direction is removed as requested.
                geom_up_vec = pt_ftl_coords - pt_fbl_coords
                norm_geom_up_vec = np.linalg.norm(geom_up_vec)
                if norm_geom_up_vec > 1e-6:
                    up_direction_for_indicator = geom_up_vec / norm_geom_up_vec
                else:
                    # Default to world Y up if geometric up is degenerate
                    up_direction_for_indicator = np.array([0.0, 1.0, 0.0])

                # Right vector along the top edge of the FAR plane (for scaling the offset)
                right_vec = pt_ftr_coords - pt_ftl_coords
                length_right_vec = np.linalg.norm(right_vec)
                # Ensure length_right_vec is not zero for tip_offset_distance calculation
                if length_right_vec < 1e-9:
                    length_right_vec = (
                        0.01  # Default small length if far plane top edge is a point
                    )

                # Midpoint of the FAR plane's top edge
                mid_top_edge = (pt_ftl_coords + pt_ftr_coords) / 2.0

                # Scale factor for the triangle height (0.3 is from TeleSculptor C++ code)
                tip_offset_distance = length_right_vec * 0.3

                # Calculate the tip point of the indicator triangle
                tip_coord = (
                    mid_top_edge + up_direction_for_indicator * tip_offset_distance
                )

                # Add the new tip point to the polydata's points
                # The existing points are 0-7. The new point will be 8.
                tip_point_id = frustum_points.InsertNextPoint(
                    tip_coord[0], tip_coord[1], tip_coord[2]
                )

                # Create the triangle cell, using Far Plane top edge points
                up_triangle = vtkTriangle()
                up_triangle.GetPointIds().SetId(0, 3)  # FTL
                up_triangle.GetPointIds().SetId(1, 2)  # FTR
                up_triangle.GetPointIds().SetId(2, tip_point_id)  # New tip point

                # Add the triangle to the polydata's cells (polygons)
                polys = individual_frustum_poly_data.GetPolys()
                if polys is None:
                    polys = vtkCellArray()
                    individual_frustum_poly_data.SetPolys(polys)
                polys.InsertNextCell(up_triangle)
                individual_frustum_poly_data.Modified()

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

        frustums_gen = (
            get_frustum_planes(camera, NEAR_CLIP, FAR_CLIP)
            for camera in camera_map.values()
        )
        update_frustums_rep(self.pipeline.frustums_rep, frustums_gen)

        self.pipeline.renderer.ResetCamera()
        self.html_view.push_camera()
        self.html_view.update()
