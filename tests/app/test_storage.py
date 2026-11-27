from linkcast.storage import AudioStorage, is_valid_name

from helpers import AUDIO


def test_lists_only_mp3_under_the_prefix(bucket):
    episodes = AudioStorage(bucket, "test/").list_episodes()
    assert [e.name for e in episodes] == ["test-episode", "second"]
    assert episodes[0].size == len(AUDIO)


def test_size_and_missing_object(bucket):
    storage = AudioStorage(bucket, "test/")
    assert storage.get_size("test-episode") == len(AUDIO)
    assert storage.get_size("nope") is None
    assert storage.get_size("../other/outside") is None


def test_read_range_is_inclusive(bucket):
    storage = AudioStorage(bucket, "test/")
    assert storage.read_range("test-episode", 2, 5) == AUDIO[2:6]


def test_iter_range_joins_chunks(bucket, monkeypatch):
    monkeypatch.setattr("linkcast.storage.CHUNK_SIZE", 100)
    storage = AudioStorage(bucket, "test/")
    assert b"".join(storage.iter_range("test-episode", 10, 1500)) == AUDIO[10:1501]


def test_name_validation():
    assert is_valid_name("test-episode")
    for bad in ["", "a/b", "..", "a..b", ".hidden", "a b"]:
        assert not is_valid_name(bad)
