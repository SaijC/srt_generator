from .const import MEDIA_TYPES

import os
import pathlib

import logging
logging.basicConfig(level=logging.INFO)

class MediaCollector:
    def __init__(self):
        self.media_files = []

    def collect_media_files(self, directory):
        self.media_files.clear()

        if not os.path.isdir(directory):
            logging.error(f"{directory} does not exist or is not a directory.")
            return

        for root, _, files in os.walk(directory, onerror=lambda e: logging.error(f"Error accessing {e.filename}: {e.strerror}")):
            for file in files:
                file_extension = pathlib.Path(file).suffix
                if not file_extension:  # No extension found
                    continue

                if file_extension.lower() not in MEDIA_TYPES:
                    continue

                file_path = os.path.join(root, file)
                self.media_files.append(file_path)

    @property
    def get_media_files(self):
        return self.media_files


if __name__ == "__main__":
    mc = MediaCollector()
    mc.collect_media_files(directory="/input")

    media_files = mc.get_media_files
    if media_files:
        for idx, file_path in enumerate(media_files, start=1):
            print(f"{idx}. {file_path}")
    else:
        logging.info("No media files found.")
