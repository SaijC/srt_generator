from src.const import MEDIA_TYPES

class MediaCollector:
    def __init__(self, directory):
        self.directory = directory
        self.media_files = []

    def collect_media_files(self):
        import os

        for root, _, files in os.walk(self.directory):
            for file in files:
                if file.split('.')[-1] in MEDIA_TYPES:
                    self.media_files.append(os.path.join(root, file))

    @property
    def get_media_files(self):
        return self.media_files

media_files = MediaCollector(directory="D:/projects/srt_data/movies").get_media_files

print(f"media_files: {len(media_files)}, {media_files}")
