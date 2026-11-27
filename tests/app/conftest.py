"""Shared fixtures of the service tests: a faked bucket, no network, no credentials.

The service dependencies are installed only by the service tests job. Where
they are missing (the repository checks job installs only pytest), these tests
are not collected.
"""

import importlib.util
from datetime import datetime, timezone

import pytest

from helpers import AUDIO, TOKEN  # noqa: F401

if importlib.util.find_spec("flask") is None:
    collect_ignore_glob = ["test_*.py"]

class FakeBlob:
    def __init__(self, name, data, created):
        self.name = name
        self.data = data
        self.size = len(data)
        self.time_created = created

    def download_as_bytes(self, start=None, end=None):
        start = 0 if start is None else start
        end = len(self.data) - 1 if end is None else end
        return self.data[start : end + 1]


class FakeBucket:
    def __init__(self, blobs):
        self.blobs = {b.name: b for b in blobs}

    def list_blobs(self, prefix=""):
        return [b for n, b in sorted(self.blobs.items()) if n.startswith(prefix)]

    def get_blob(self, name):
        return self.blobs.get(name)


@pytest.fixture
def blobs():
    return [
        FakeBlob("test/test-episode.mp3", AUDIO, datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)),
        FakeBlob("test/second.mp3", b"abc", datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)),
        FakeBlob("test/notes.txt", b"x", datetime(2026, 11, 3, tzinfo=timezone.utc)),
        FakeBlob("other/outside.mp3", b"x", datetime(2026, 11, 3, tzinfo=timezone.utc)),
    ]


@pytest.fixture
def bucket(blobs):
    return FakeBucket(blobs)


@pytest.fixture
def client(bucket):
    from linkcast.app import Config, create_app
    from linkcast.storage import AudioStorage

    config = Config(feed_token=TOKEN, audio_bucket="fake-bucket")
    app = create_app(config, AudioStorage(bucket, config.audio_prefix))
    return app.test_client()
