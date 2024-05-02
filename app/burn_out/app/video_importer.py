from kwiver.vital.algo import VideoInput, MetadataMapIO
from kwiver.vital.config import read_config_file
from kwiver.vital.types import Timestamp, SimpleMetadataMap
from pathlib import Path
import logging
from multiprocessing import Process, Queue

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class VideoImporter:
    """Helper class to extract and save metadata in a different process"""

    def __init__(self):
        self.task_handle = None
        self.task_queue = Queue()
        self.process = Process(target=_worker, args=(self.task_queue,))
        self.process.start()

    def run(self, video_path, config_path):
        """Extract metadata from the video given in video_path using a reader
        constructed based on config_path"""
        self.task_queue.put((_extract_metadata, (video_path, config_path)))

    def write(self, path, config_path):
        """Write previously extracted data to path"""
        self.task_queue.put((_write, (path, config_path)))

    def close(self):
        """Terminate the process"""
        self.task_queue.put(None)


def _worker(queue):
    data = None
    for func, args in iter(queue.get, None):
        if func == _extract_metadata:
            data = func(*args)
        elif func == _write:
            if data is not None:
                func(data, *args)
            else:
                logger.warning("No metadata to write")
        else:
            raise RuntimeError("Unhandled worker function")
    print("worker_done")


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
    while video_reader.next_frame(current_timestamp):  # && !d->canceled)
        if not current_timestamp.has_valid_frame():
            continue

        frame = current_timestamp.get_frame()
        metadata = video_reader.frame_metadata()

        if len(metadata) > 0:
            frame_metadata[frame] = metadata

    # if (d->canceled)
    # {
    #  // invalidate the metadata map
    #  metadataMap = nullptr;
    # }

    # emit this->progressChanged(QString("Loading video complete"), 100);
    # emit this->completed(metadataMap);
    print("Done reading metadata")
    return frame_metadata


def _write(data, metadata_path, config_path):
    logger.debug("writing metadata")
    writer_type = "json"
    if Path(metadata_path).suffix == ".csv":
        writer_type = "csv"

    config = read_config_file(config_path)
    config["metadata_writer:type"] = writer_type

    #  config->set_value("metadata_writer:type", writer_type,
    #                    "Type of serialization to use");
    #  d->freestandingConfig->merge_config(config);
    #
    try:
        metadata_serializer = MetadataMapIO.set_nested_algo_configuration(
            "metadata_writer", config
        )
        if metadata_serializer is None:
            logger.error("Error saving metadata")
        #    if (!metadataMapIO)
        #    {
        #      QMessageBox::critical(
        #        this, QStringLiteral("Error saving metadata"),
        #        QStringLiteral("Improper configuration settings. "
        #                       "Please see the log."));
        #      return;
        #    }
        smm = SimpleMetadataMap(data)
        metadata_serializer.save(metadata_path, data=smm)
        logger.debug(f"Wrote metadata to {metadata_path}")
        print("wrote_metadata")
    except Exception as error:
        logger.error(f"Error saving metadata \n {error}")


#    QMessageBox::critical(
#      this, QStringLiteral("Error saving metadata"),
#      QStringLiteral("Failed to save metadata: ") +
#      QString::fromLocal8Bit(e.what()));
