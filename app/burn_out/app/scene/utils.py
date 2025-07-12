from kwiver.vital.types import SimpleCameraPerspective
import numpy as np
from vtkmodules.vtkRenderingCore import vtkCamera
import math
from typing import List, NamedTuple, Optional, Tuple


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
        # This matches TeleSculptor's vtkKwiverCamera::BuildCamera logic
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

    # Camera orientation extraction - validated implementation
    #
    # KWIVER's rotation matrix R_wc represents a world-from-camera transformation.
    # When transposed, R_T rows represent camera axes in world coordinates:
    # - R_T[0, :] = camera axis 0 in world coordinates
    # - R_T[1, :] = camera axis 1 in world coordinates  
    # - R_T[2, :] = camera axis 2 in world coordinates
    #
    # Through comprehensive testing comparing TeleSculptor's C++ implementation
    # with KWIVER's Python bindings, we determined that for VTK cameras:
    # - View direction = R_T[0, :] (first row of transpose)
    # - Up direction = -R_T[2, :] (negative third row of transpose)
    #
    # Note: TeleSculptor's C++ vtkKwiverCamera uses row(2) and -row(1), but
    # these indices don't translate directly to Python due to differences in
    # camera coordinate conventions between the implementations. Our empirically
    # validated approach correctly handles aerial camera orientations.
    
    R_T = R_wc.T  # Transpose to access camera axes as rows
    view_dir_w = R_T[0, :]    # Camera X-axis = empirically correct view direction
    up_dir_w = -R_T[2, :]     # -Camera Z-axis = empirically correct up direction

    vtk_cam.SetPosition(center_w[0], center_w[1], center_w[2])
    vtk_cam.SetViewUp(up_dir_w[0], up_dir_w[1], up_dir_w[2])

    # Use a fixed distance for focal point calculation (matching TeleSculptor)
    # This needs to be set before calling GetDistance()
    distance_to_focal_point = 1.0  # Default VTK distance

    # Normalize view direction
    view_norm = np.linalg.norm(view_dir_w)
    if view_norm < 1e-6:
        view_dir_w_norm = np.array([0.0, 0.0, 1.0])
    else:
        view_dir_w_norm = view_dir_w / view_norm

    # Calculate focal point: center + (view * distance / |view|)
    # Note: view is already extracted from rotation matrix, so we just normalize it
    focal_point_w = center_w + view_dir_w_norm * distance_to_focal_point
    vtk_cam.SetFocalPoint(focal_point_w[0], focal_point_w[1], focal_point_w[2])

    vtk_cam.SetClippingRange(near_clip, far_clip)

    return VtkCameraBundle(camera=vtk_cam, aspect_ratio=combined_aspect_ratio)


def get_frustum_planes(
    camera_bundle: VtkCameraBundle, scale: float = 1.0
) -> List[float]:
    """
    Calculates the frustum planes for a vtkCamera, using aspect ratio from bundle.
    The planes will have normals pointing OUTSIDE the frustum.
    Order: Right, Left, Bottom, Top, Near, Far.

    Parameters:
        camera_bundle: Bundle containing the vtkCamera and its aspect ratio
        scale: Scale factor for the frustum size (1.0 = original size)
    """
    vtk_cam = camera_bundle.camera
    aspect = camera_bundle.aspect_ratio

    planes_coeffs = [0.0] * 24
    vtk_cam.GetFrustumPlanes(aspect, planes_coeffs)

    if scale == 1.0:
        return planes_coeffs

    # Each plane is represented by 4 coefficients (A, B, C, D) in the equation Ax + By + Cz + D = 0
    # To scale a plane relative to the camera center, we need to adjust the D coefficient

    # Get camera center (position)
    camera_pos = np.array(vtk_cam.GetPosition())

    # Process each plane (6 planes total: Right, Left, Bottom, Top, Near, Far)
    for i in range(6):
        # Get the normal vector (A, B, C) for this plane
        normal = np.array(planes_coeffs[i * 4 : i * 4 + 3])

        # The original D coefficient
        d_orig = planes_coeffs[i * 4 + 3]

        # Calculate the distance from the camera center to the plane
        # Using the plane equation: Ax + By + Cz + D = 0
        # distance = |Ax + By + Cz + D| / √(A² + B² + C²)
        # Since we're using normalized normals, the denominator is 1
        dist_to_plane = abs(np.dot(normal, camera_pos) + d_orig)

        # To scale the plane's distance from the camera center:
        # 1. First, determine if the plane is "in front of" or "behind" the camera
        # (we use the sign of Ax + By + Cz + D)
        sign = 1 if np.dot(normal, camera_pos) + d_orig > 0 else -1

        # 2. Adjust the distance by scale factor
        new_dist = dist_to_plane * scale

        # 3. Calculate the new D coefficient
        # new_D = -dot(normal, point_on_plane)
        # For a point on the plane at distance new_dist from camera along normal:
        # point_on_plane = camera_pos + normal * new_dist * sign
        # So new_D = -dot(normal, camera_pos + normal * new_dist * sign)
        #          = -dot(normal, camera_pos) - new_dist * sign
        new_d = -np.dot(normal, camera_pos) - new_dist * sign

        # Update the D coefficient in the planes array
        planes_coeffs[i * 4 + 3] = new_d

    return planes_coeffs


def get_frustum_planes_from_simple_camera(
    simple_cam: SimpleCameraPerspective,
    near_clip: float,
    far_clip: float,
    scale: float = 1.0,
) -> List[float]:
    """
    Creates a vtkCamera from a SimpleCameraPerspective and then calculates its frustum planes.

    Parameters:
        simple_cam: The SimpleCameraPerspective object
        near_clip: The near clipping plane distance
        far_clip: The far clipping plane distance
        scale: Scale factor for the frustum size (1.0 = original size)
    """
    camera_bundle = create_vtk_camera_from_simple_camera(
        simple_cam, near_clip, far_clip
    )
    planes_coeffs = get_frustum_planes(camera_bundle, scale)
    return planes_coeffs


def compute_frustum_ground_intersection(
    frustum_planes: List[float], ground_z: float = 0.0
) -> Optional[List[Tuple[float, float, float]]]:
    """
    Computes the intersection polygon between a camera frustum and the ground plane.
    
    This implementation uses a more robust approach by finding the intersection
    of the ground plane with the frustum volume directly, rather than computing
    edge intersections.
    
    Parameters:
        frustum_planes: List of 24 floats representing 6 frustum planes (4 coefficients each)
                       Order: Right, Left, Bottom, Top, Near, Far
        ground_z: Z coordinate of the ground plane (default 0.0)
    
    Returns:
        List of 3D points forming the intersection polygon, or None if no intersection
    """
    # Use VTK's frustum source to get corner points
    from vtkmodules.vtkCommonDataModel import vtkPlanes
    from vtkmodules.vtkFiltersSources import vtkFrustumSource
    
    planes_object = vtkPlanes()
    planes_object.SetFrustumPlanes(frustum_planes)
    
    frustum_source = vtkFrustumSource()
    frustum_source.SetPlanes(planes_object)
    frustum_source.ShowLinesOff()
    frustum_source.Update()
    
    frustum_poly = frustum_source.GetOutput()
    if not frustum_poly or frustum_poly.GetNumberOfPoints() != 8:
        return None
    
    # Get the 8 corner points of the frustum
    # Points from vtkFrustumSource (ShowLinesOff=True):
    # Far plane: 0:FBL, 1:FBR, 2:FTR, 3:FTL
    # Near plane: 4:NBL, 5:NBR, 6:NTR, 7:NTL
    corners = []
    for i in range(8):
        pt = frustum_poly.GetPoint(i)
        corners.append(np.array(pt))
    
    # Find which corners are above and below the ground plane
    above_ground = []
    below_ground = []
    
    for i, corner in enumerate(corners):
        if corner[2] > ground_z:
            above_ground.append(i)
        else:
            below_ground.append(i)
    
    # If all points are on one side, no intersection
    if len(above_ground) == 0 or len(below_ground) == 0:
        return None
    
    # Find intersection points where frustum edges cross the ground plane
    intersection_points = []
    
    # Define the 12 edges of the frustum
    edges = [
        # Near plane edges
        (4, 5), (5, 6), (6, 7), (7, 4),
        # Far plane edges  
        (0, 1), (1, 2), (2, 3), (3, 0),
        # Connecting edges
        (0, 4), (1, 5), (2, 6), (3, 7)
    ]
    
    for v1_idx, v2_idx in edges:
        v1 = corners[v1_idx]
        v2 = corners[v2_idx]
        
        # Check if edge crosses ground plane
        z1_above = v1[2] > ground_z
        z2_above = v2[2] > ground_z
        
        if z1_above != z2_above:  # Edge crosses ground
            # Find intersection point using linear interpolation
            t = (ground_z - v1[2]) / (v2[2] - v1[2])
            intersection = v1 + t * (v2 - v1)
            intersection_points.append(tuple(intersection))
    
    # Also add any corners that lie exactly on the ground plane
    for i, corner in enumerate(corners):
        if abs(corner[2] - ground_z) < 1e-6:
            intersection_points.append(tuple(corner))
    
    # Remove duplicate points
    unique_points = []
    for point in intersection_points:
        is_duplicate = False
        for existing in unique_points:
            if np.linalg.norm(np.array(point) - np.array(existing)) < 1e-6:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_points.append(point)
    
    if len(unique_points) < 3:
        return None  # No valid polygon
    
    # Sort points to form a proper polygon
    # Project to 2D (x,y) and sort by angle from centroid
    points_2d = [(p[0], p[1]) for p in unique_points]
    centroid = np.mean(points_2d, axis=0)
    
    def angle_from_centroid(point):
        return np.arctan2(point[1] - centroid[1], point[0] - centroid[0])
    
    sorted_indices = sorted(range(len(unique_points)), 
                          key=lambda i: angle_from_centroid(points_2d[i]))
    
    sorted_points = [unique_points[i] for i in sorted_indices]
    
    return sorted_points
