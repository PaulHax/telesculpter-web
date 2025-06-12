from kwiver.vital.types import SimpleCameraPerspective
import numpy as np
from vtkmodules.vtkRenderingCore import vtkCamera
import math
from typing import List, NamedTuple


class VtkCameraBundle(NamedTuple):
    camera: vtkCamera
    aspect_ratio: float


def create_vtk_camera_from_simple_camera(
    simple_cam: SimpleCameraPerspective, near_clip: float, far_clip: float
) -> VtkCameraBundle:
    """
    Creates and configures a vtkCamera from a SimpleCameraPerspective object,
    similar to the logic in vtkKwiverCamera::BuildCamera.
    Returns a bundle containing the camera and its calculated aspect ratio.
    """
    vtk_cam = vtkCamera()
    ci = simple_cam.intrinsics()

    image_width = float(ci.image_width())
    image_height = float(ci.image_height())
    principal_point = ci.principal_point()

    if image_width <= 0 or image_height <= 0:
        # Estimate from principal point if not set or invalid
        if principal_point[0] > 0 and principal_point[1] > 0:
            image_width = principal_point[0] * 2.0
            image_height = principal_point[1] * 2.0
        else:
            # Fallback if principal point is also not useful
            image_width = 1.0
            image_height = 1.0

    pixel_aspect = ci.aspect_ratio()  # pixel_height / pixel_width
    if pixel_aspect == 0:
        pixel_aspect = 1.0  # Assume square pixels

    focal_length = ci.focal_length()

    # Avoid division by zero for critical parameters
    if image_height == 0:
        image_height = 1e-6
    if image_width == 0:
        image_width = 1e-6
    if focal_length == 0:
        focal_length = 1e-6

    combined_aspect_ratio = pixel_aspect * image_width / image_height

    # FOV (SetViewAngle is in degrees, for the vertical direction)
    fov_rad = 2.0 * math.atan(0.5 * image_height / focal_length)
    fov_deg = math.degrees(fov_rad)
    vtk_cam.SetViewAngle(fov_deg)

    # Camera pose
    center_w = np.array(simple_cam.center().tolist())
    R_wc = np.array(simple_cam.rotation().matrix())  # World from Camera matrix

    view_dir_w = R_wc[:, 2]
    up_dir_w = -R_wc[:, 1]

    vtk_cam.SetPosition(center_w[0], center_w[1], center_w[2])
    vtk_cam.SetViewUp(up_dir_w[0], up_dir_w[1], up_dir_w[2])

    distance_to_focal_point = vtk_cam.GetDistance()
    if np.linalg.norm(view_dir_w) < 1e-6:
        view_dir_w_norm = np.array([0.0, 0.0, 1.0])
    else:
        view_dir_w_norm = view_dir_w / np.linalg.norm(view_dir_w)

    focal_point_w = center_w + view_dir_w_norm * distance_to_focal_point
    vtk_cam.SetFocalPoint(focal_point_w[0], focal_point_w[1], focal_point_w[2])

    vtk_cam.SetClippingRange(near_clip, far_clip)

    return VtkCameraBundle(camera=vtk_cam, aspect_ratio=combined_aspect_ratio)


def get_frustum_planes(
    camera_bundle: VtkCameraBundle,
) -> List[float]:
    """
    Calculates the frustum planes for a vtkCamera, using aspect ratio from bundle.
    The planes will have normals pointing OUTSIDE the frustum.
    Order: Right, Left, Bottom, Top, Near, Far.
    """
    vtk_cam = camera_bundle.camera
    aspect = camera_bundle.aspect_ratio

    planes_coeffs = [0.0] * 24
    vtk_cam.GetFrustumPlanes(aspect, planes_coeffs)

    return planes_coeffs


def get_frustum_planes_from_simple_camera(
    simple_cam: SimpleCameraPerspective, near_clip: float, far_clip: float
) -> List[float]:
    """
    Creates a vtkCamera from a SimpleCameraPerspective and then calculates its frustum planes.
    """
    camera_bundle = create_vtk_camera_from_simple_camera(
        simple_cam, near_clip, far_clip
    )
    planes_coeffs = get_frustum_planes(camera_bundle)
    return planes_coeffs
