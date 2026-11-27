"""Read access to the private audio bucket: listing and ranged reads."""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

# Object names served to the podcast app: a plain file name, no slashes.
_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
_EXTENSION = ".mp3"
CHUNK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class Episode:
    """One MP3 object: its name without the extension, size and creation time."""

    name: str
    size: int
    created: datetime


def is_valid_name(name: str) -> bool:
    return bool(_NAME_RE.fullmatch(name)) and ".." not in name


class AudioStorage:
    """Lists and reads the MP3 objects under a prefix of one bucket.

    ``bucket`` is a ``google.cloud.storage.Bucket`` (or anything with the same
    ``list_blobs`` and ``get_blob`` methods, which is how the tests fake it).
    """

    def __init__(self, bucket, prefix: str):
        self._bucket = bucket
        self._prefix = prefix

    @classmethod
    def from_bucket_name(cls, bucket_name: str, prefix: str) -> "AudioStorage":
        # Imported here so that the tests and the token check do not need the
        # Google client to be configured.
        from google.cloud import storage

        return cls(storage.Client().bucket(bucket_name), prefix)

    def list_episodes(self) -> list[Episode]:
        """Return the MP3 objects directly under the prefix, oldest first."""
        episodes = []
        for blob in self._bucket.list_blobs(prefix=self._prefix):
            file_name = blob.name[len(self._prefix):]
            if not file_name.endswith(_EXTENSION):
                continue
            name = file_name[: -len(_EXTENSION)]
            if not is_valid_name(name):
                continue
            episodes.append(Episode(name=name, size=blob.size or 0, created=blob.time_created))
        episodes.sort(key=lambda e: (e.created, e.name))
        return episodes

    def get_size(self, name: str) -> int | None:
        """Return the size in bytes of an episode, or None if it does not exist."""
        if not is_valid_name(name):
            return None
        blob = self._bucket.get_blob(self._prefix + name + _EXTENSION)
        return None if blob is None else blob.size or 0

    def read_range(self, name: str, start: int, end: int) -> bytes:
        """Read bytes ``start`` to ``end`` inclusive of an episode."""
        blob = self._bucket.get_blob(self._prefix + name + _EXTENSION)
        if blob is None:
            raise FileNotFoundError(name)
        return blob.download_as_bytes(start=start, end=end)

    def iter_range(self, name: str, start: int, end: int) -> Iterator[bytes]:
        """Yield bytes ``start`` to ``end`` inclusive in chunks."""
        position = start
        while position <= end:
            last = min(position + CHUNK_SIZE - 1, end)
            yield self.read_range(name, position, last)
            position = last + 1
