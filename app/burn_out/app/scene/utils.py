import numpy as np
from kwiver.vital.types import SimpleCameraPerspective  # For type hinting


def get_frustum_planes(
    camera: SimpleCameraPerspective, near_clip: float, far_clip: float
):
    """
    Calculates the frustum planes for a SimpleCameraPerspective.

    Args:
        camera (SimpleCameraPerspective): The camera object.
        near_clip (float): Distance to the near clipping plane.
        far_clip (float): Distance to the far clipping plane.

    Returns:
        list[float]: A flat list of 24 floats representing the 6 frustum planes
                     (Right, Left, Bottom, Top, Near, Far), each defined by
                     4 coefficients (A, B, C, D). Normals point inwards.
    """
    C_w = np.array(camera.center().tolist())
    # kwiver.vital.types.RotationD().matrix() returns a list of 3 lists of 3 floats
    R_wc_list = camera.rotation().matrix()
    R_wc = np.array(R_wc_list)

    z_axis_w = R_wc[:, 2]  # View direction

    intr = camera.intrinsics()
    f = intr.focal_length()
    W = float(intr.image_width())  # Corrected: use intrinsics object
    H = float(intr.image_height())  # Corrected: use intrinsics object
    pp = intr.principal_point()
    px = pp[0]
    py = pp[1]

    # Avoid division by zero if dimensions or focal length are zero
    if W == 0:
        W = 1e-6
    if H == 0:
        H = 1e-6
    if f == 0:
        f = 1e-6

    # Normals point inwards (positive side of plane Ax+By+Cz+D=0 is "inside")

    # Near Plane
    n_near_w = z_axis_w
    D_near = -np.dot(n_near_w, C_w) - near_clip
    plane_near = [n_near_w[0], n_near_w[1], n_near_w[2], D_near]

    # Far Plane
    n_far_w = -z_axis_w
    D_far = np.dot(z_axis_w, C_w) + far_clip
    plane_far = [n_far_w[0], n_far_w[1], n_far_w[2], D_far]

    # Side planes (normals in camera coordinates, then transformed to world)
    # Assuming camera local axes: X right, Y up (consistent with common 3D graphics), Z forward (out of screen)
    # And image coordinates: origin top-left, X right, Y down.
    # The original formulas are kept, assuming they align with kwiver's camera model conventions.

    # Left Plane: Normal (f,0,px) in cam_coords points right (inward).
    n_L_c = np.array([f, 0.0, px])
    n_L_w = R_wc @ n_L_c
    D_L = -np.dot(n_L_w, C_w)
    plane_left = [n_L_w[0], n_L_w[1], n_L_w[2], D_L]

    # Right Plane: Normal (-f,0, W-px) in cam_coords points left (inward).
    n_R_c = np.array([-f, 0.0, (W - px)])
    n_R_w = R_wc @ n_R_c
    D_R = -np.dot(n_R_w, C_w)
    plane_right = [n_R_w[0], n_R_w[1], n_R_w[2], D_R]

    # Top Plane: Normal (0,f,py) in cam_coords points up (inward, assuming camera Y up).
    n_T_c = np.array([0.0, f, py])
    n_T_w = R_wc @ n_T_c
    D_T = -np.dot(n_T_w, C_w)
    plane_top = [n_T_w[0], n_T_w[1], n_T_w[2], D_T]

    # Bottom Plane: Normal (0,-f, H-py) in cam_coords points down (inward).
    n_B_c = np.array([0.0, -f, (H - py)])
    n_B_w = R_wc @ n_B_c
    D_B = -np.dot(n_B_w, C_w)
    plane_bottom = [n_B_w[0], n_B_w[1], n_B_w[2], D_B]

    # Order for vtkCamera::GetFrustumPlanes: Right, Left, Bottom, Top, Near, Far
    ordered_planes = [
        plane_right,
        plane_left,
        plane_bottom,
        plane_top,
        plane_near,
        plane_far,
    ]

    flat_coeffs = [coeff for plane in ordered_planes for coeff in plane]
    return flat_coeffs
