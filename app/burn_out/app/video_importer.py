from kwiver.vital.algo import VideoInput, MetadataMapIO
from kwiver.vital.config import read_config_file
from kwiver.vital.types import Timestamp, SimpleMetadataMap
from pathlib import Path
from kwiver.vital import plugin_management
from kwiver.vital import vital_logging
import logging
import sys
import asyncio
from multiprocessing import Queue
from burn_out.app.metadata_serializer import serialize, deserialize
from burn_out.multiprocess_worker import (
    create_worker,
    send_task,
    await_result,
    close_worker,
    cancel_worker,
)

logger = vital_logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Configure a StreamHandler to output to stdout
stream_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(name)s - %(message)s")
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def video_worker(task_queue: Queue, result_queue: Queue):
    """Worker function for video metadata processing."""
    original_metadata = None  # Keep original metadata for writing
    vpm = plugin_management.plugin_manager_instance()
    vpm.load_all_plugins()

    while True:
        try:
            task = task_queue.get()
            if task is None:
                break

            if isinstance(task, tuple) and len(task) == 2:
                func_name, args = task

                if func_name == "extract_metadata":
                    original_metadata = _extract_metadata(*args)
                    json_metadata = serialize(original_metadata)
                    result_queue.put(json_metadata)
                elif func_name == "write_metadata":
                    if original_metadata is not None:
                        _write_metadata(original_metadata, *args)
                        result_queue.put("write_complete")
                    else:
                        logger.warning("No metadata to write")
                        result_queue.put("write_error")
        except (KeyboardInterrupt, SystemExit):
            break
        except Exception as e:
            logger.error(f"Worker error: {e}")
            result_queue.put(f"error: {e}")


class VideoImporter:
    """Helper class to extract and save metadata using functional multiprocess worker."""

    def __init__(self, metadata_callback):
        self.metadata_callback = metadata_callback
        self.worker = create_worker(video_worker)

    def run(self, video_path, config_path):
        """Extract metadata from the video given in video_path using a reader
        constructed based on config_path"""
        self.worker = send_task(
            self.worker, ("extract_metadata", (video_path, config_path))
        )

        # Start a task to await results and call metadata callback
        asyncio.create_task(self._await_metadata_results())

    def write(self, path, config_path):
        """Write previously extracted data to path"""
        self.worker = send_task(self.worker, ("write_metadata", (path, config_path)))

    def cancel(self):
        """Cancel current operations and restart worker"""
        self.worker = cancel_worker(self.worker)

    def close(self):
        """Close the worker process"""
        close_worker(self.worker)

    async def _await_metadata_results(self):
        """Await metadata results from the worker process and call the metadata callback"""
        self.worker, result = await await_result(self.worker)

        if (
            result
            and result != "write_complete"
            and result != "write_error"
            and not result.startswith("error:")
        ):
            deserialized_metadata = deserialize(result)
            if deserialized_metadata is not None and self.metadata_callback:
                if asyncio.iscoroutinefunction(self.metadata_callback):
                    await self.metadata_callback(deserialized_metadata)
                else:
                    self.metadata_callback(deserialized_metadata)


def _extract_metadata(video_path, config_path):
    config = read_config_file(str(config_path))
    if not VideoInput.check_nested_algo_configuration("video_reader", config):
        logger.warn("An error was found in the video source algorithm configuration.")
        return

    video_reader = VideoInput.set_nested_algo_configuration("video_reader", config)
    video_reader.open(video_path)

    frame_metadata = dict()

    # If no metadata stream, exit early
    # TODO TypeError: Unable to convert function return value to a Python type! The signature was
    #      (self: kwiver.vital.algo.algos.VideoInput) -> kwiver::vital::algorithm_capabilities
    # if not video_reader.get_implementation_capabilities().has_capability(VideoInput.HAS_METADATA):
    #  video_reader.close()
    #  return

    current_timestamp = Timestamp()
    while video_reader.next_frame(current_timestamp):
        if not current_timestamp.has_valid_frame():
            continue

        frame = current_timestamp.get_frame()
        metadata = video_reader.frame_metadata()
        if len(metadata) > 0:
            frame_metadata[frame] = metadata

    logger.debug("Done reading metadata")
    return frame_metadata


def _write_metadata(data, metadata_path, config_path):
    logger.debug("writing metadata")
    writer_type = "json"
    if Path(metadata_path).suffix == ".csv":
        writer_type = "csv"

    config = read_config_file(config_path)
    config["metadata_writer:type"] = writer_type

    # TODO: check what this exactly does in C++
    #  d->freestandingConfig->merge_config(config);
    #
    try:
        metadata_serializer = MetadataMapIO.set_nested_algo_configuration(
            "metadata_writer", config
        )
        if metadata_serializer is None:
            logger.error("Error saving metadata")
        smm = SimpleMetadataMap(data)
        metadata_serializer.save(metadata_path, data=smm)
        logger.debug(f"Wrote metadata to {metadata_path}")
    except Exception as error:
        logger.error(f"Error saving metadata \n {error}")
