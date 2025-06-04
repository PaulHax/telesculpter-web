from trame.decorators import TrameApp
from kwiver.vital.types import (
    SFMConstraints,
    SimpleCameraPerspective,
    SimpleCameraIntrinsics,
    RotationD,
)
from kwiver.vital.types import metadata_tags as mt
import numpy as np


def make_camera_map(sfm_constraints, metadata):
    intrinsics = SimpleCameraIntrinsics()
    base_camera = SimpleCameraPerspective()
    base_camera.set_intrinsics(intrinsics)

    # only keep first metadata element for each frame
    md_map = {
        frame_id: metadata.get_vector(frame_id)[0] for frame_id in metadata.frames()
    }

    # Get local geographic coordinate system
    local_geo_cs = sfm_constraints.local_geo_cs

    # Initialize cameras from metadata
    camera_map = initialize_cameras_with_metadata(md_map, base_camera, local_geo_cs)

    # Update the SFM constraints with the updated local coordinate system
    sfm_constraints.local_geo_cs = local_geo_cs

    return camera_map


def intrinsics_from_metadata(metadata, camera_intrinsics=None):
    """
    Create camera intrinsics from metadata
    Port of C++ intrinsics_from_metadata function
    """
    if camera_intrinsics is None:
        intrinsics = SimpleCameraIntrinsics()
    else:
        intrinsics = SimpleCameraIntrinsics(
            camera_intrinsics
        )  # Try to compute focal length from slant range and target width
    if metadata.has(mt.tags.VITAL_META_SLANT_RANGE) and metadata.has(
        mt.tags.VITAL_META_TARGET_WIDTH
    ):
        slant_range = metadata.find(mt.tags.VITAL_META_SLANT_RANGE).as_double()
        target_width = metadata.find(mt.tags.VITAL_META_TARGET_WIDTH).as_double()

        # Default image width if not available
        image_width = intrinsics.image_width() if intrinsics.image_width() > 0 else 1920

        # Compute focal length: focal = (image_width * slant_range) / target_width
        focal_length = (image_width * slant_range) / target_width
        intrinsics.set_focal_length(
            focal_length
        )  # Try to compute focal length from horizontal FOV
    elif metadata.has(mt.tags.VITAL_META_SENSOR_HORIZONTAL_FOV):
        import math

        horizontal_fov_rad = metadata.find(
            mt.tags.VITAL_META_SENSOR_HORIZONTAL_FOV
        ).as_double()
        # Default image width if not available
        image_width = intrinsics.image_width() if intrinsics.image_width() > 0 else 1920

        # Compute focal length from FOV: focal = (image_width/2) / tan(horizontal_fov/2)
        focal_length = (image_width / 2.0) / math.tan(horizontal_fov_rad / 2.0)
        intrinsics.set_focal_length(
            focal_length
        )  # If vertical FOV is also available, compute aspect ratio
        if metadata.has(mt.tags.VITAL_META_SENSOR_VERTICAL_FOV):
            vertical_fov_rad = metadata.find(
                mt.tags.VITAL_META_SENSOR_VERTICAL_FOV
            ).as_double()
            image_height = (
                intrinsics.image_height() if intrinsics.image_height() > 0 else 1080
            )

            focal_y = (image_height / 2.0) / math.tan(vertical_fov_rad / 2.0)
            aspect_ratio = focal_length / focal_y
            intrinsics.set_aspect_ratio(aspect_ratio)

    return intrinsics


def update_camera_from_metadata(camera, metadata):
    """
    Update camera pose from metadata
    Port of C++ update_camera_from_metadata function
    """

    if metadata.has(mt.tags.VITAL_META_SENSOR_LOCATION):
        sensor_loc = metadata.find(mt.tags.VITAL_META_SENSOR_LOCATION).data
        camera.set_center(sensor_loc.location())

    # Get platform and sensor orientation angles
    platform_yaw = 0.0
    platform_pitch = 0.0
    platform_roll = 0.0
    sensor_yaw = 0.0
    sensor_pitch = 0.0
    sensor_roll = 0.0

    if metadata.has(mt.tags.VITAL_META_PLATFORM_HEADING_ANGLE):
        platform_yaw = metadata.find(
            mt.tags.VITAL_META_PLATFORM_HEADING_ANGLE
        ).as_double()
    if metadata.has(mt.tags.VITAL_META_PLATFORM_PITCH_ANGLE):
        platform_pitch = metadata.find(
            mt.tags.VITAL_META_PLATFORM_PITCH_ANGLE
        ).as_double()
    if metadata.has(mt.tags.VITAL_META_PLATFORM_ROLL_ANGLE):
        platform_roll = metadata.find(
            mt.tags.VITAL_META_PLATFORM_ROLL_ANGLE
        ).as_double()

    if metadata.has(mt.tags.VITAL_META_SENSOR_YAW_ANGLE):
        sensor_yaw = metadata.find(mt.tags.VITAL_META_SENSOR_YAW_ANGLE).as_double()
    if metadata.has(mt.tags.VITAL_META_SENSOR_PITCH_ANGLE):
        sensor_pitch = metadata.find(mt.tags.VITAL_META_SENSOR_PITCH_ANGLE).as_double()
    if metadata.has(mt.tags.VITAL_META_SENSOR_ROLL_ANGLE):
        sensor_roll = (
            metadata.find(mt.tags.VITAL_META_SENSOR_ROLL_ANGLE).as_double()
        )  # Create rotation from platform and sensor angles using UAS convention
    # In UAS convention, we need to combine platform rotation and sensor rotation
    # Platform rotation: yaw, pitch, roll of the platform/vehicle
    # Sensor rotation: additional yaw, pitch, roll of the sensor relative to platform

    # Total yaw, pitch, roll is the combination of platform and sensor angles
    total_yaw = platform_yaw + sensor_yaw
    total_pitch = platform_pitch + sensor_pitch
    total_roll = platform_roll + sensor_roll

    # Create rotation from combined angles (in radians)
    import math

    total_yaw_rad = math.radians(total_yaw)
    total_pitch_rad = math.radians(total_pitch)
    total_roll_rad = math.radians(total_roll)

    rotation = RotationD(total_yaw_rad, total_pitch_rad, total_roll_rad)

    camera.set_rotation(rotation)
    return camera


def initialize_cameras_with_metadata(metadata_map, base_camera, local_geo_cs):
    """
    Initialize cameras from metadata map
    Port of C++ initialize_cameras_with_metadata function
    """

    camera_map = {}

    if not metadata_map:
        return camera_map  # Set up local coordinate system origin from first available metadata
    origin_set = False
    for frame_id, metadata in metadata_map.items():
        if metadata.has(mt.tags.VITAL_META_SENSOR_LOCATION):
            if not origin_set:
                try:
                    sensor_loc = metadata.find(mt.tags.VITAL_META_SENSOR_LOCATION).data
                    local_geo_cs.geo_origin = sensor_loc
                    origin_set = True
                except RuntimeError as e:
                    if "No geo-conversion functor is registered" in str(e):
                        print(
                            f"Warning: Geodetic conversion not available, skipping geo origin setup: {e}"
                        )
                        # Continue without setting geo origin
                        pass
                    else:
                        raise
            break

    # Create cameras from metadata
    camera_centers = []

    for frame_id, metadata in metadata_map.items():
        # Create camera intrinsics from metadata
        camera_intrinsics = intrinsics_from_metadata(metadata, base_camera.intrinsics())

        # Create new camera with updated intrinsics
        camera = SimpleCameraPerspective(base_camera)
        camera.set_intrinsics(camera_intrinsics)

        # Update camera pose from metadata
        camera = update_camera_from_metadata(camera, metadata)

        # Add to camera map
        camera_map[frame_id] = camera

        # Collect camera centers for local origin update
        camera_centers.append(camera.center())

    # Update local origin to mean of camera positions if we have cameras
    if camera_centers and origin_set:
        # Convert to local coordinates and compute mean
        local_centers = []
        for center in camera_centers:
            local_center = local_geo_cs.geo_to_local(center)
            local_centers.append([local_center.x(), local_center.y(), local_center.z()])

        # Compute mean center
        mean_center = np.mean(
            local_centers, axis=0
        )  # Convert back to geographic coordinates and update origin
        from kwiver.vital.types import Vector3d

        mean_local = Vector3d(mean_center[0], mean_center[1], mean_center[2])
        mean_geo = local_geo_cs.local_to_geo(mean_local)
        try:
            local_geo_cs.geo_origin = mean_geo
        except RuntimeError as e:
            if "No geo-conversion functor is registered" in str(e):
                print(
                    f"Warning: Geodetic conversion not available, skipping geo origin update: {e}"
                )
            else:
                raise

    return camera_map


@TrameApp()
class Scene:
    def __init__(self, server):
        self.server = server

    def set_metadata(self, metadata):
        self.metadata = metadata
        self.sfm_constraints = SFMConstraints()
        self.sfm_constraints.metadata = metadata

        self.camera_map = make_camera_map(self.sfm_constraints, metadata)

        self.server.context.camera_map = {
            frame_id: {
                "center": camera.center().tolist(),
                "rotation": camera.rotation().quaternion(),
                # "intrinsics": {
                #     "focal_length": camera.intrinsics().focal_length(),
                #     "principal_point": [
                #         camera.intrinsics().principal_point_x(),
                #         camera.intrinsics().principal_point_y(),
                #     ],
                #     "aspect_ratio": camera.intrinsics().aspect_ratio(),
                #     "skew": camera.intrinsics().skew(),
                # },
            }
            for frame_id, camera in self.camera_map.items()
        }
        self.server.controller.update_camera_map()
