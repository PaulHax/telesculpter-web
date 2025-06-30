from trame.decorators import TrameApp
from kwiver.vital.types import (
    SFMConstraints,
    SimpleCameraPerspective,
    SimpleCameraIntrinsics,
    RotationD,
    ned_to_enu,
    LocalCartesian,
    GeoPoint,
    geodesy,
)
from kwiver.vital.types import metadata_tags as mt
from kwiver.vital import vital_logging
import math
import numpy as np
import logging
from .metadata_diagnostics import analyze_metadata_content

logger = vital_logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def make_camera_map(sfm_constraints, metadata, ignore_metadata=False):
    intrinsics = SimpleCameraIntrinsics()
    base_camera = SimpleCameraPerspective()
    base_camera.set_intrinsics(intrinsics)

    # only keep first metadata element for each frame
    md_map = {
        frame_id: metadata.get_vector(frame_id)[0] for frame_id in metadata.frames()
    }

    local_geo_cs = sfm_constraints.local_geo_cs

    if ignore_metadata:
        logger.info("Ignoring metadata - creating cameras with default poses")
        camera_map = {}
        for frame_id in md_map.keys():
            camera_map[frame_id] = SimpleCameraPerspective(base_camera)
    else:
        analyze_metadata_content(md_map)
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
        intrinsics = SimpleCameraIntrinsics(camera_intrinsics)

    if metadata.has(mt.tags.VITAL_META_IMAGE_WIDTH):
        md_image_width = metadata.find(mt.tags.VITAL_META_IMAGE_WIDTH).as_uint64()
        if md_image_width > 0:
            intrinsics.set_image_width(int(md_image_width))

    if metadata.has(mt.tags.VITAL_META_IMAGE_HEIGHT):
        md_image_height = metadata.find(mt.tags.VITAL_META_IMAGE_HEIGHT).as_uint64()
        if md_image_height > 0:
            intrinsics.set_image_height(int(md_image_height))

    # Try to compute focal length
    if metadata.has(mt.tags.VITAL_META_SLANT_RANGE) and metadata.has(
        mt.tags.VITAL_META_TARGET_WIDTH
    ):
        slant_range = metadata.find(mt.tags.VITAL_META_SLANT_RANGE).as_double()
        target_width = metadata.find(mt.tags.VITAL_META_TARGET_WIDTH).as_double()

        image_width = intrinsics.image_width() if intrinsics.image_width() > 0 else 1920

        focal_length = (image_width * slant_range) / target_width
        intrinsics.set_focal_length(focal_length)
    elif metadata.has(mt.tags.VITAL_META_SENSOR_HORIZONTAL_FOV):
        horizontal_fov_rad = math.radians(
            metadata.find(mt.tags.VITAL_META_SENSOR_HORIZONTAL_FOV).as_double()
        )
        image_width = intrinsics.image_width() if intrinsics.image_width() > 0 else 1920

        focal_length = (image_width / 2.0) / math.tan(horizontal_fov_rad / 2.0)
        intrinsics.set_focal_length(focal_length)

        # If vertical FOV is also available, compute aspect ratio
        if metadata.has(mt.tags.VITAL_META_SENSOR_VERTICAL_FOV):
            vertical_fov_rad = math.radians(
                metadata.find(mt.tags.VITAL_META_SENSOR_VERTICAL_FOV).as_double()
            )
            image_height = (
                intrinsics.image_height() if intrinsics.image_height() > 0 else 1080
            )

            focal_y = (image_height / 2.0) / math.tan(vertical_fov_rad / 2.0)
            # Note: focal_length here is from horizontal FOV
            aspect_ratio = focal_length / focal_y
            intrinsics.set_aspect_ratio(aspect_ratio)

    # Set principal point to the center of the image if it's currently (0,0)
    # and image dimensions are now known and non-zero.
    # This mirrors the C++ kwiver::vital::intrinsics_from_metadata logic.
    if intrinsics.image_width() > 0 and intrinsics.image_height() > 0:
        pp_x = intrinsics.image_width() / 2.0
        pp_y = intrinsics.image_height() / 2.0
        intrinsics.set_principal_point([pp_x, pp_y])

    return intrinsics


def update_camera_from_metadata(camera, metadata):
    """
    Update camera pose from metadata
    Port of C++ update_camera_from_metadata function
    """

    if metadata.has(mt.tags.VITAL_META_SENSOR_LOCATION):
        sensor_loc_object = metadata.find(mt.tags.VITAL_META_SENSOR_LOCATION).data
        if sensor_loc_object is not None and callable(
            getattr(sensor_loc_object, "location", None)
        ):
            camera.set_center(sensor_loc_object.location())

    # Get platform and sensor orientation angles
    platform_yaw_deg = 0.0
    platform_pitch_deg = 0.0
    platform_roll_deg = 0.0
    sensor_yaw_deg = 0.0
    sensor_pitch_deg = 0.0
    sensor_roll_deg = (
        0.0  # Initialize sensor_roll_deg, C++ defaults this to 0 if tag is missing
    )

    has_platform_yaw = False
    has_platform_pitch = False
    has_platform_roll = False
    has_sensor_yaw = False
    has_sensor_pitch = False

    if metadata.has(mt.tags.VITAL_META_PLATFORM_HEADING_ANGLE):
        platform_yaw_deg = metadata.find(
            mt.tags.VITAL_META_PLATFORM_HEADING_ANGLE
        ).as_double()
        has_platform_yaw = True
    if metadata.has(mt.tags.VITAL_META_PLATFORM_PITCH_ANGLE):
        platform_pitch_deg = metadata.find(
            mt.tags.VITAL_META_PLATFORM_PITCH_ANGLE
        ).as_double()
        has_platform_pitch = True
    if metadata.has(mt.tags.VITAL_META_PLATFORM_ROLL_ANGLE):
        platform_roll_deg = metadata.find(
            mt.tags.VITAL_META_PLATFORM_ROLL_ANGLE
        ).as_double()
        has_platform_roll = True

    if metadata.has(mt.tags.VITAL_META_SENSOR_REL_AZ_ANGLE):
        sensor_yaw_deg = metadata.find(
            mt.tags.VITAL_META_SENSOR_REL_AZ_ANGLE
        ).as_double()
        has_sensor_yaw = True
    if metadata.has(mt.tags.VITAL_META_SENSOR_REL_EL_ANGLE):
        sensor_pitch_deg = metadata.find(
            mt.tags.VITAL_META_SENSOR_REL_EL_ANGLE
        ).as_double()
        has_sensor_pitch = True
    if metadata.has(mt.tags.VITAL_META_SENSOR_REL_ROLL_ANGLE):
        sensor_roll_deg = metadata.find(
            mt.tags.VITAL_META_SENSOR_REL_ROLL_ANGLE
        ).as_double()

    # Condition to match C++ logic in camera_from_metadata.cxx
    # Sensor roll is used in uas_ypr_to_rotation, and its NaN status matters.
    # The C++ check requires platform YPR and sensor YP to be present and all angles (including sensor roll) to be non-NaN.
    condition_met = (
        has_platform_yaw
        and has_platform_pitch
        and has_platform_roll
        and has_sensor_yaw
        and has_sensor_pitch  # Sensor roll presence isn't strictly required for the condition, as it defaults to 0
        and not (
            math.isnan(platform_yaw_deg)
            or math.isnan(platform_pitch_deg)
            or math.isnan(platform_roll_deg)
            or math.isnan(sensor_yaw_deg)
            or math.isnan(sensor_pitch_deg)
            or math.isnan(sensor_roll_deg)
        )
    )

    if not condition_met:
        return camera
    platform_yaw_rad = math.radians(platform_yaw_deg)
    platform_pitch_rad = math.radians(platform_pitch_deg)
    platform_roll_rad = math.radians(platform_roll_deg)

    sensor_yaw_rad = math.radians(sensor_yaw_deg)
    sensor_pitch_rad = math.radians(sensor_pitch_deg)
    sensor_roll_rad = math.radians(sensor_roll_deg)

    platform_rotation_ned = RotationD(
        platform_yaw_rad, platform_pitch_rad, platform_roll_rad
    )

    sensor_rotation_ned = RotationD(sensor_yaw_rad, sensor_pitch_rad, sensor_roll_rad)

    combined_rotation_ned = platform_rotation_ned * sensor_rotation_ned

    final_rotation_enu = ned_to_enu(combined_rotation_ned)

    camera.set_rotation(final_rotation_enu)

    return camera


def initialize_cameras_with_metadata(metadata_map, base_camera, local_geo_cs):
    """
    Initialize cameras from metadata map
    Port of C++ initialize_cameras_with_metadata function
    """

    logger.debug(f"Initializing {len(metadata_map)} cameras from metadata")

    camera_map = {}

    origin_set = False
    for frame_id, metadata in metadata_map.items():
        if metadata.has(mt.tags.VITAL_META_SENSOR_LOCATION) and not origin_set:
            sensor_loc = metadata.find(mt.tags.VITAL_META_SENSOR_LOCATION).data
            local_geo_cs.geo_origin = sensor_loc
            origin_set = True
            break

    # Create cameras from metadata
    camera_centers = []
    cameras_with_orientation = 0

    for frame_id, metadata in metadata_map.items():
        # Create camera intrinsics from metadata
        camera_intrinsics = intrinsics_from_metadata(metadata, base_camera.intrinsics())

        # Create new camera with updated intrinsics
        camera = SimpleCameraPerspective(base_camera)
        camera.set_intrinsics(camera_intrinsics)

        # Check if this frame has complete orientation metadata before updating
        has_complete_orientation = (
            metadata.has(mt.tags.VITAL_META_PLATFORM_HEADING_ANGLE)
            and metadata.has(mt.tags.VITAL_META_PLATFORM_PITCH_ANGLE)
            and metadata.has(mt.tags.VITAL_META_PLATFORM_ROLL_ANGLE)
            and metadata.has(mt.tags.VITAL_META_SENSOR_REL_AZ_ANGLE)
            and metadata.has(mt.tags.VITAL_META_SENSOR_REL_EL_ANGLE)
        )

        if has_complete_orientation:
            cameras_with_orientation += 1

        # Update camera pose from metadata
        camera = update_camera_from_metadata(camera, metadata)

        # Add to camera map
        camera_map[frame_id] = camera

        # Collect camera centers for local origin update
        camera_centers.append(camera.center())

    # Update local origin to mean of camera positions if we have cameras
    if camera_centers and origin_set:
        # Create LocalCartesian converter with current origin
        origin_geo = local_geo_cs.geo_origin
        converter = LocalCartesian(origin_geo, 0.0)

        # Convert to local coordinates and compute mean
        local_centers = []
        for center in camera_centers:
            # Convert numpy array center to GeoPoint, then to local cartesian
            center_geo = GeoPoint(center, geodesy.SRID.lat_lon_WGS84)
            local_center = converter.convert_to_cartesian(center_geo)
            local_centers.append([local_center[0], local_center[1], local_center[2]])

        # Compute mean center
        mean_center = np.mean(local_centers, axis=0)

        # Convert back to geographic coordinates and update origin
        mean_local = np.array([mean_center[0], mean_center[1], mean_center[2]])
        mean_geo = GeoPoint()
        converter.convert_from_cartesian(mean_local, mean_geo)

        local_geo_cs.geo_origin = mean_geo

    logger.info(
        f"Camera initialization complete: {cameras_with_orientation}/{len(metadata_map)} cameras have orientation metadata"
    )

    return camera_map


@TrameApp()
class Scene:
    def __init__(self, server):
        self.server = server
        self.ignore_metadata = False  # TeleSculptor-style configuration option

    def set_ignore_metadata(self, ignore):
        """Set whether to ignore metadata for camera initialization (like TeleSculptor)"""
        self.ignore_metadata = ignore
        logger.info(f"Metadata usage {'disabled' if ignore else 'enabled'}")

    def set_metadata(self, metadata):
        self.metadata = metadata
        self.sfm_constraints = SFMConstraints()
        self.sfm_constraints.metadata = metadata

        camera_map = make_camera_map(
            self.sfm_constraints, metadata, self.ignore_metadata
        )
        self.server.controller.update_camera_map(camera_map)
