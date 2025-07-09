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

from trame.decorators import TrameApp, change
from trame.widgets import vtk as vtk_widgets
from trame.app import asynchronous
import logging

from .scene.utils import (
    get_frustum_planes_from_simple_camera,  # Added
)
from .utils import create_throttler


colors = vtkNamedColors()
logger = logging.getLogger(__name__)

NEAR_CLIP = 0.01
# TeleSculptor uses different far clip for active vs inactive cameras
FAR_CLIP_INACTIVE = 4.0  # TeleSculptor's NonActiveCameraRepLength default
FAR_CLIP_ACTIVE = 15.0  # TeleSculptor's ActiveCameraRepLength default
FRUSTUM_SCALE = 1
UPDATE_THROTTLE_INTERVAL = 0.1  # 10fps during video playback

# TeleSculptor default UI scale values
CAMERA_UI_SCALE = 0.25  # Default scale for active camera
INACTIVE_SCALE_FACTOR = 0.1  # Inactive cameras are 0.1x active scale


def calculate_frustum_far_clip(camera_centers: Sequence[Sequence[float]], 
                               is_active: bool = False) -> float:
    """
    Calculate frustum far clip distance based on scene bounds.
    Follows TeleSculptor's approach: 0.9 * bbox diagonal * UI scale factors.
    
    Args:
        camera_centers: List of camera center coordinates
        is_active: Whether this is for the active camera (larger frustum)
    
    Returns:
        Far clip distance for frustum
    """
    if not camera_centers:
        return FAR_CLIP_ACTIVE if is_active else FAR_CLIP_INACTIVE
    
    # Compute bounding box diagonal like TeleSculptor's updateScale
    camera_array = np.array(camera_centers)
    bbox_min = np.min(camera_array, axis=0)
    bbox_max = np.max(camera_array, axis=0)
    bbox_diagonal = np.linalg.norm(bbox_max - bbox_min)
    
    # TeleSculptor uses 0.9 * diagonal for base scale
    base_camera_scale = 0.9 * bbox_diagonal
    
    # Calculate far clip based on active/inactive status
    if is_active:
        frustum_far_clip = base_camera_scale * CAMERA_UI_SCALE
        min_clip = FAR_CLIP_ACTIVE
    else:
        frustum_far_clip = base_camera_scale * CAMERA_UI_SCALE * INACTIVE_SCALE_FACTOR
        min_clip = FAR_CLIP_INACTIVE
    
    # Ensure minimum far clip distance
    return max(frustum_far_clip, min_clip)


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


class ActiveFrustum_Rep(NamedTuple):
    poly_data: vtkPolyData
    mapper: vtkPolyDataMapper
    actor: vtkActor


class GroundPlan_Rep(NamedTuple):
    poly_data: vtkPolyData
    mapper: vtkPolyDataMapper
    actor: vtkActor


class Pipeline(NamedTuple):
    positions_rep: Positions_Rep
    frustums_rep: Frustums_Rep
    active_frustum_rep: ActiveFrustum_Rep
    ground_plan_rep: GroundPlan_Rep
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
    # actor.SetUseBounds(False)
    actor.SetVisibility(False)  # Hide dummy frustum initially

    renderer.AddActor(actor)

    return Frustums_Rep(
        poly_data=output_poly_data,
        mapper=mapper,
        actor=actor,
        append_poly_data=append_filter,
        dummy_input_poly_data=dummy_pd,
    )


def create_active_frustum_rep(renderer: vtkRenderer):
    poly_data = vtkPolyData()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(poly_data)

    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(colors.GetColor3d("White"))
    actor.GetProperty().SetRepresentationToWireframe()
    # actor.SetUseBounds(False)

    renderer.AddActor(actor)

    return ActiveFrustum_Rep(
        poly_data=poly_data,
        mapper=mapper,
        actor=actor,
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


def update_active_frustum_rep(active_frustum_rep: ActiveFrustum_Rep, frustum_planes):
    if frustum_planes:
        build_camera_frustum(frustum_planes, active_frustum_rep.poly_data)
    else:
        active_frustum_rep.poly_data.Initialize()
    active_frustum_rep.poly_data.Modified()


def create_ground_plan_grid(
    size: float = 100.0, divisions: int = 20, z_level: float = 0.0
):
    """
    Creates a grid-based ground plan centered at origin.

    Args:
        size: Total size of the grid in world units
        divisions: Number of grid divisions per side
        z_level: Z coordinate for the ground plane
    """
    points = vtkPoints()
    lines = vtkCellArray()

    half_size = size / 2.0
    step = size / divisions

    # Create horizontal lines (constant Y, varying X)
    for i in range(divisions + 1):
        y = -half_size + i * step

        # Line from (-half_size, y, z_level) to (half_size, y, z_level)
        p1_id = points.InsertNextPoint(-half_size, y, z_level)
        p2_id = points.InsertNextPoint(half_size, y, z_level)

        lines.InsertNextCell(2)
        lines.InsertCellPoint(p1_id)
        lines.InsertCellPoint(p2_id)

    # Create vertical lines (constant X, varying Y)
    for i in range(divisions + 1):
        x = -half_size + i * step

        # Line from (x, -half_size, z_level) to (x, half_size, z_level)
        p1_id = points.InsertNextPoint(x, -half_size, z_level)
        p2_id = points.InsertNextPoint(x, half_size, z_level)

        lines.InsertNextCell(2)
        lines.InsertCellPoint(p1_id)
        lines.InsertCellPoint(p2_id)

    poly_data = vtkPolyData()
    poly_data.SetPoints(points)
    poly_data.SetLines(lines)

    return poly_data


def create_ground_plan_rep(renderer: vtkRenderer):
    """
    Creates a ground plan representation showing a reference grid.
    """
    poly_data = create_ground_plan_grid()

    mapper = vtkPolyDataMapper()
    mapper.SetInputData(poly_data)

    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(colors.GetColor3d("DarkGray"))
    actor.GetProperty().SetOpacity(0.3)
    actor.GetProperty().SetLineWidth(1.0)

    renderer.AddActor(actor)

    return GroundPlan_Rep(
        poly_data=poly_data,
        mapper=mapper,
        actor=actor,
    )


def calculate_scene_scale_factor(camera_centers: Sequence[Sequence[float]]) -> float:
    """
    Calculate appropriate scale factor for visualization, similar to TeleSculptor's approach.

    TeleSculptor normalizes scenes to reasonable visualization units. For very small
    coordinate scenes (< 1.0 unit extent), we scale up for better visualization.
    """
    if not camera_centers:
        return 1.0

    camera_array = np.array(camera_centers)

    # Calculate scene extent
    x_extent = np.max(camera_array[:, 0]) - np.min(camera_array[:, 0])
    y_extent = np.max(camera_array[:, 1]) - np.min(camera_array[:, 1])
    z_extent = np.max(camera_array[:, 2]) - np.min(camera_array[:, 2])
    max_extent = max(x_extent, y_extent, z_extent)

    # If scene is very small (typical for SfM without proper scaling), scale it up
    # Target: scene should have extent of roughly 10-100 units for good visualization
    if max_extent < 1.0:
        # Scale to make largest dimension around 50 units
        target_size = 50.0
        scale_factor = target_size / max_extent
    elif max_extent > 1000.0:
        # Scale down very large scenes
        target_size = 100.0
        scale_factor = target_size / max_extent
    else:
        # Scene size is reasonable
        scale_factor = 1.0

    return scale_factor


def update_ground_plan_position(
    ground_plan_rep: GroundPlan_Rep,
    camera_centers: Sequence[Sequence[float]],
    scale_factor: float,
):
    """
    Updates the ground plan position using TeleSculptor's approach with provided scale factor.

    Following TeleSculptor's canonical transform estimation:
    - Uses provided scale factor for consistency with other representations
    - Positions ground plane below 5th percentile of camera heights
    - Scales to 1.5x maximum horizontal extent of camera trajectory
    - Ensures proper orientation relative to camera viewing direction
    """
    if not camera_centers:
        return

    camera_array = np.array(camera_centers)

    # Apply scaling to camera positions using provided scale factor
    scaled_camera_array = camera_array * scale_factor

    # Calculate robust bounds (following TeleSculptor's getBounds approach)
    x_min, x_max = np.min(scaled_camera_array[:, 0]), np.max(scaled_camera_array[:, 0])
    y_min, y_max = np.min(scaled_camera_array[:, 1]), np.max(scaled_camera_array[:, 1])
    z_values = scaled_camera_array[:, 2]

    # Use 5th percentile for ground plane height (TeleSculptor's height_percentile = 0.05)
    ground_z = np.percentile(z_values, 5)

    # Calculate scene diagonal for scaling (TeleSculptor's groundScale calculation)
    x_extent = x_max - x_min
    y_extent = y_max - y_min
    max_horizontal_extent = max(x_extent, y_extent)

    # TeleSculptor uses 1.5x scale factor for ground plane relative to scene bounds
    ground_scale = max(1.5 * max_horizontal_extent, 10.0)  # Minimum size

    # Calculate grid center (centroid of camera positions in X-Y plane)
    center_x = np.mean(scaled_camera_array[:, 0])
    center_y = np.mean(scaled_camera_array[:, 1])

    # Create grid with TeleSculptor-style positioning
    # Grid is centered on camera trajectory centroid, scaled appropriately
    new_poly_data = create_ground_plan_grid_with_center(
        size=ground_scale,
        center_x=center_x,
        center_y=center_y,
        z_level=ground_z,
        divisions=20,
    )

    ground_plan_rep.poly_data.DeepCopy(new_poly_data)
    ground_plan_rep.poly_data.Modified()


def create_ground_plan_grid_with_center(
    size: float, center_x: float, center_y: float, z_level: float, divisions: int = 20
):
    """
    Creates a grid-based ground plan centered at specified coordinates.
    Matches TeleSculptor's ground plane generation approach.
    """
    points = vtkPoints()
    lines = vtkCellArray()

    half_size = size / 2.0
    step = size / divisions

    # Create horizontal lines (constant Y, varying X)
    for i in range(divisions + 1):
        y = center_y - half_size + i * step

        # Line from (center_x - half_size, y, z_level) to (center_x + half_size, y, z_level)
        p1_id = points.InsertNextPoint(center_x - half_size, y, z_level)
        p2_id = points.InsertNextPoint(center_x + half_size, y, z_level)

        lines.InsertNextCell(2)
        lines.InsertCellPoint(p1_id)
        lines.InsertCellPoint(p2_id)

    # Create vertical lines (constant X, varying Y)
    for i in range(divisions + 1):
        x = center_x - half_size + i * step

        # Line from (x, center_y - half_size, z_level) to (x, center_y + half_size, z_level)
        p1_id = points.InsertNextPoint(x, center_y - half_size, z_level)
        p2_id = points.InsertNextPoint(x, center_y + half_size, z_level)

        lines.InsertNextCell(2)
        lines.InsertCellPoint(p1_id)
        lines.InsertCellPoint(p2_id)

    poly_data = vtkPolyData()
    poly_data.SetPoints(points)
    poly_data.SetLines(lines)

    return poly_data


def create_pipeline():
    renderer = vtkRenderer()
    renderer.ResetCamera()
    renderer.SetBackground(0, 0, 0)

    render_window = vtkRenderWindow()
    render_window.AddRenderer(renderer)

    return Pipeline(
        positions_rep=create_camera_position_rep(renderer),
        frustums_rep=create_frustums_rep(renderer),
        active_frustum_rep=create_active_frustum_rep(renderer),
        ground_plan_rep=create_ground_plan_rep(renderer),
        renderer=renderer,
        render_window=render_window,
    )


@TrameApp()
class WorldView:
    def __init__(self, server):
        self.server = server
        self.server.controller.update_camera_map.add(self.update_camera_map)
        self.pipeline = create_pipeline()
        self.active_camera_id = None
        self.camera_map = {}
        self._camera_reset_done = False  # Track if camera has been reset already
        self._throttled_update = create_throttler(UPDATE_THROTTLE_INTERVAL)
        self._scene_scale_factor = 1.0  # Shared scale factor for all representations

    def create_view(self):
        self.html_view = vtk_widgets.VtkLocalView(
            self.pipeline.render_window, box_selection=False
        )

        self.server.controller.on_server_ready.add(self.html_view.update)
        self.server.controller.reset_world_camera = self.html_view.reset_camera

        # Reset camera to show full ground plan initially
        self.pipeline.renderer.ResetCamera()
        self.html_view.push_camera()

    def update_camera_map(self, camera_map):
        self.camera_map = camera_map
        self._update_cameras()
        # Update active camera for initial display when camera map is loaded
        if camera_map:
            self.active_camera_id = self.server.state.video_current_frame
            self._update_active_camera_rep()

    @change("video_current_frame")
    def update_active_camera(self, **_):
        self.active_camera_id = self.server.state.video_current_frame
        self._update_active_camera_rep()

    def _update_active_camera_rep(self):
        camera_map = getattr(self, "camera_map", {})
        active_camera_id = getattr(self, "active_camera_id", None)
        active_camera = camera_map.get(active_camera_id)

        if active_camera:
            # Calculate active camera frustum with dynamic scaling
            camera_centers = [cam.center().tolist() for cam in self.camera_map.values()]
            active_frustum_far_clip = calculate_frustum_far_clip(camera_centers, is_active=True)

            active_frustum_planes = get_frustum_planes_from_simple_camera(
                active_camera,  # Use original camera, not scaled
                NEAR_CLIP,
                active_frustum_far_clip,
                FRUSTUM_SCALE,
            )
            update_active_frustum_rep(
                self.pipeline.active_frustum_rep, active_frustum_planes
            )
            self.pipeline.active_frustum_rep.actor.SetVisibility(True)
        else:
            update_active_frustum_rep(self.pipeline.active_frustum_rep, None)
            self.pipeline.active_frustum_rep.actor.SetVisibility(False)

        # Use throttled updates to prevent interference with video timing
        # Fixes WSL-specific bug where VTK updates interfere with video playback timing
        asynchronous.create_task(self._throttled_update(self.html_view.update))

    def _update_cameras(self):
        camera_map = getattr(self, "camera_map", {})
        centers = [camera.center().tolist() for camera in camera_map.values()]

        # Calculate shared scene scale factor once for all representations
        self._scene_scale_factor = (
            calculate_scene_scale_factor(centers) if centers else 1.0
        )

        # Use original camera positions (not scaled) for visualization
        # TeleSculptor doesn't scale camera positions, only frustum sizes
        update_positions_rep(self.pipeline.positions_rep, centers)

        # Calculate dynamic frustum scale based on scene bounds
        frustum_far_clip = calculate_frustum_far_clip(centers, is_active=False)

        # Generate frustums from original cameras (not scaled positions)
        # Only the frustum size is adjusted based on scene scale
        frustums = (
            get_frustum_planes_from_simple_camera(
                cam,
                NEAR_CLIP,
                frustum_far_clip,
                FRUSTUM_SCALE,
            )
            for cam in camera_map.values()
        )

        update_frustums_rep(self.pipeline.frustums_rep, frustums, 10)

        # Show frustums when cameras are available, hide dummy otherwise
        self.pipeline.frustums_rep.actor.SetVisibility(len(camera_map) > 0)

        # Update ground plan position using TeleSculptor's approach with shared scale factor
        if centers:
            update_ground_plan_position(
                self.pipeline.ground_plan_rep, centers, self._scene_scale_factor
            )

        # Only reset camera the first time with a valid camera_map
        if camera_map and not self._camera_reset_done:
            self.pipeline.renderer.ResetCamera()
            self.html_view.push_camera()
            self._camera_reset_done = True

        self.html_view.update()
