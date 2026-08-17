from .const import MEDIA_TYPES
import os

class MediaCollector:
    def __init__(self):
        self.media_files = []

    def collect_media_files(self, directory):
        self.media_files.clear()
        
        for root, _, files in os.walk(directory):
            for file in files:
                file_extension = file.rsplit('.', 1)[-1]
                if file_extension.lower() not in MEDIA_TYPES:
                    continue

                file_path = os.path.join(root, file)
                self.media_files.append(file_path)

    @property
    def get_media_files(self):
        return self.media_files


if __name__ == "__main__":
    mc = MediaCollector()
    mc.collect_media_files(directory="./input/movies")
    print(len(mc.get_media_files), mc.get_media_files)
