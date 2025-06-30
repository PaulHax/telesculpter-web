"""
Metadata diagnostic utilities for debugging video metadata content
"""

from kwiver.vital.types import metadata_tags as mt
from kwiver.vital import vital_logging
import logging
import math

logger = vital_logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def analyze_metadata_content(metadata_map):
    """
    Analyze metadata content and report what orientation data is available
    Similar to TeleSculptor's metadata analysis capabilities
    """

    if not metadata_map:
        logger.info("No metadata found in video")
        return

    total_frames = len(metadata_map)
    logger.info(f"Analyzing metadata for {total_frames} frames")

    # Analyze orientation angles in detail
    analyze_orientation_angles(metadata_map)

    # Track which metadata tags are present across all frames
    orientation_tags = {
        "platform_heading": mt.tags.VITAL_META_PLATFORM_HEADING_ANGLE,
        "platform_pitch": mt.tags.VITAL_META_PLATFORM_PITCH_ANGLE,
        "platform_roll": mt.tags.VITAL_META_PLATFORM_ROLL_ANGLE,
        "sensor_azimuth": mt.tags.VITAL_META_SENSOR_REL_AZ_ANGLE,
        "sensor_elevation": mt.tags.VITAL_META_SENSOR_REL_EL_ANGLE,
        "sensor_roll": mt.tags.VITAL_META_SENSOR_REL_ROLL_ANGLE,
    }

    position_tags = {
        "sensor_location": mt.tags.VITAL_META_SENSOR_LOCATION,
        "frame_center": mt.tags.VITAL_META_FRAME_CENTER,
    }

    camera_tags = {
        "horizontal_fov": mt.tags.VITAL_META_SENSOR_HORIZONTAL_FOV,
        "vertical_fov": mt.tags.VITAL_META_SENSOR_VERTICAL_FOV,
        "image_width": mt.tags.VITAL_META_IMAGE_WIDTH,
        "image_height": mt.tags.VITAL_META_IMAGE_HEIGHT,
    }

    # Count how many frames have each tag
    tag_counts = {}
    sample_values = {}

    for tag_name, tag in {**orientation_tags, **position_tags, **camera_tags}.items():
        count = 0
        sample_value = None

        for frame_id, metadata in metadata_map.items():
            if metadata.has(tag):
                count += 1
                if sample_value is None:
                    try:
                        if tag == mt.tags.VITAL_META_SENSOR_LOCATION:
                            sensor_loc = metadata.find(tag).data
                            if sensor_loc and hasattr(sensor_loc, "location"):
                                loc = sensor_loc.location()
                                sample_value = (
                                    f"[{loc[0]:.6f}, {loc[1]:.6f}, {loc[2]:.1f}]"
                                )
                        else:
                            sample_value = f"{metadata.find(tag).as_double():.2f}"
                    except Exception:
                        sample_value = "present"

        tag_counts[tag_name] = count
        sample_values[tag_name] = sample_value

    # Report orientation metadata availability
    logger.info("=== ORIENTATION METADATA ANALYSIS ===")
    orientation_complete = 0

    for frame_id, metadata in metadata_map.items():
        has_all_orientation = all(
            metadata.has(tag) for tag in orientation_tags.values()
        )
        if has_all_orientation:
            orientation_complete += 1

    logger.info(
        f"Frames with complete orientation data: {orientation_complete}/{total_frames}"
    )

    for tag_name, count in tag_counts.items():
        if tag_name in orientation_tags:
            status = "✓" if count == total_frames else "✗" if count == 0 else "~"
            sample = (
                f" (sample: {sample_values[tag_name]})"
                if sample_values[tag_name]
                else ""
            )
            logger.info(f"  {status} {tag_name}: {count}/{total_frames} frames{sample}")

    # Report position metadata
    logger.info("=== POSITION METADATA ANALYSIS ===")
    for tag_name, count in tag_counts.items():
        if tag_name in position_tags:
            status = "✓" if count == total_frames else "✗" if count == 0 else "~"
            sample = (
                f" (sample: {sample_values[tag_name]})"
                if sample_values[tag_name]
                else ""
            )
            logger.info(f"  {status} {tag_name}: {count}/{total_frames} frames{sample}")

    # Report camera metadata
    logger.info("=== CAMERA METADATA ANALYSIS ===")
    for tag_name, count in tag_counts.items():
        if tag_name in camera_tags:
            status = "✓" if count == total_frames else "✗" if count == 0 else "~"
            sample = (
                f" (sample: {sample_values[tag_name]})"
                if sample_values[tag_name]
                else ""
            )
            logger.info(f"  {status} {tag_name}: {count}/{total_frames} frames{sample}")

    # Summary recommendation
    if orientation_complete == total_frames:
        logger.info(
            "✓ RESULT: All frames have complete orientation metadata - initial camera poses will use orientation data"
        )
    elif orientation_complete > 0:
        logger.info(
            f"~ RESULT: {orientation_complete}/{total_frames} frames have complete orientation metadata - partial usage"
        )
    else:
        logger.info(
            "✗ RESULT: No complete orientation metadata found - cameras will use default orientations"
        )


def log_first_frame_metadata(metadata_map, max_tags=20):
    """
    Log all metadata tags present in the first frame for debugging
    """
    if not metadata_map:
        return

    first_frame_id = next(iter(metadata_map))
    first_metadata = metadata_map[first_frame_id]

    logger.debug(f"=== FIRST FRAME METADATA TAGS (frame {first_frame_id}) ===")

    # Get all available tags (this is a simplified approach)
    orientation_tags = [
        "VITAL_META_PLATFORM_HEADING_ANGLE",
        "VITAL_META_PLATFORM_PITCH_ANGLE",
        "VITAL_META_PLATFORM_ROLL_ANGLE",
        "VITAL_META_SENSOR_REL_AZ_ANGLE",
        "VITAL_META_SENSOR_REL_EL_ANGLE",
        "VITAL_META_SENSOR_REL_ROLL_ANGLE",
    ]

    # Check for key orientation tags specifically
    for tag_name in orientation_tags:
        if hasattr(mt.tags, tag_name):
            tag = getattr(mt.tags, tag_name)
            if first_metadata.has(tag):
                try:
                    value = first_metadata.find(tag).as_double()
                    logger.debug(f"  ✓ {tag_name}: {value:.2f}")
                except Exception:
                    logger.debug(f"  ✓ {tag_name}: present")
            else:
                logger.debug(f"  ✗ {tag_name}: missing")


def analyze_orientation_angles(metadata_map):
    """
    Analyze orientation angles in metadata and log detailed information about
    missing angles and sample values for debugging
    """
    if not metadata_map:
        return

    total_frames = len(metadata_map)
    orientation_tags = {
        "platform_heading": mt.tags.VITAL_META_PLATFORM_HEADING_ANGLE,
        "platform_pitch": mt.tags.VITAL_META_PLATFORM_PITCH_ANGLE,
        "platform_roll": mt.tags.VITAL_META_PLATFORM_ROLL_ANGLE,
        "sensor_azimuth": mt.tags.VITAL_META_SENSOR_REL_AZ_ANGLE,
        "sensor_elevation": mt.tags.VITAL_META_SENSOR_REL_EL_ANGLE,
        "sensor_roll": mt.tags.VITAL_META_SENSOR_REL_ROLL_ANGLE,
    }

    # Find first frame with complete orientation to log sample values
    sample_logged = False
    frames_with_missing_angles = 0

    for frame_id, metadata in metadata_map.items():
        missing_angles = []
        sample_values = {}

        # Check each orientation angle
        for angle_name, tag in orientation_tags.items():
            if metadata.has(tag):
                try:
                    value = metadata.find(tag).as_double()
                    if not math.isnan(value):
                        sample_values[angle_name] = value
                    else:
                        missing_angles.append(angle_name)
                except Exception:
                    missing_angles.append(angle_name)
            else:
                missing_angles.append(angle_name)

        # Log sample values from first complete frame
        if not sample_logged and len(missing_angles) == 0:
            logger.debug(f"Sample orientation metadata from frame {frame_id}:")
            logger.debug(
                f"  Platform: heading={sample_values.get('platform_heading', 0):.1f}°, "
                f"pitch={sample_values.get('platform_pitch', 0):.1f}°, "
                f"roll={sample_values.get('platform_roll', 0):.1f}°"
            )
            logger.debug(
                f"  Sensor: azimuth={sample_values.get('sensor_azimuth', 0):.1f}°, "
                f"elevation={sample_values.get('sensor_elevation', 0):.1f}°, "
                f"roll={sample_values.get('sensor_roll', 0):.1f}°"
            )
            sample_logged = True

        # Count frames with missing angles
        if missing_angles:
            frames_with_missing_angles += 1
            # Log details for first few frames with missing data
            if frames_with_missing_angles <= 3:
                logger.debug(
                    f"Frame {frame_id} missing orientation angles: {missing_angles}"
                )

    # Log summary of missing angles
    if frames_with_missing_angles > 0:
        logger.debug(
            f"Total frames with incomplete orientation metadata: {frames_with_missing_angles}/{total_frames}"
        )
        if frames_with_missing_angles > 3:
            logger.debug("  (Additional frames with missing data not shown)")
