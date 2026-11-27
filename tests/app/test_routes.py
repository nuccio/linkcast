import logging
from xml.etree import ElementTree as ET

import pytest

from helpers import AUDIO, TOKEN

FEED = f"/feed/{TOKEN}/feed.xml"
EPISODE = f"/feed/{TOKEN}/episodes/test-episode.mp3"


def test_feed_with_the_right_token(client):
    response = client.get(FEED, base_url="http://svc.example.test")
    assert response.status_code == 200
    assert response.headers["X-Robots-Tag"] == "noindex"
    assert response.mimetype == "application/rss+xml"
    root = ET.fromstring(response.data)
    urls = [e.get("url") for e in root.iter("enclosure")]
    # Enclosures are built from the request, with https and the same token.
    assert urls == [
        f"https://svc.example.test/feed/{TOKEN}/episodes/test-episode.mp3",
        f"https://svc.example.test/feed/{TOKEN}/episodes/second.mp3",
    ]
    assert b"<itunes:block>Yes</itunes:block>" in response.data


def test_episode_full(client):
    response = client.get(EPISODE)
    assert response.status_code == 200
    assert response.mimetype == "audio/mpeg"
    assert response.headers["Accept-Ranges"] == "bytes"
    assert response.data == AUDIO
    assert response.headers["X-Robots-Tag"] == "noindex"


def test_episode_range(client):
    response = client.get(EPISODE, headers={"Range": "bytes=10-19"})
    assert response.status_code == 206
    assert response.data == AUDIO[10:20]
    assert response.headers["Content-Range"] == f"bytes 10-19/{len(AUDIO)}"
    assert response.headers["Content-Length"] == "10"


def test_episode_open_ended_and_suffix_range(client):
    open_ended = client.get(EPISODE, headers={"Range": "bytes=2000-"})
    assert open_ended.status_code == 206
    assert open_ended.data == AUDIO[2000:]
    suffix = client.get(EPISODE, headers={"Range": "bytes=-5"})
    assert suffix.status_code == 206
    assert suffix.data == AUDIO[-5:]


def test_unsatisfiable_range(client):
    response = client.get(EPISODE, headers={"Range": "bytes=5000-6000"})
    assert response.status_code == 416
    assert response.headers["Content-Range"] == f"bytes */{len(AUDIO)}"


def test_head_has_no_body(client):
    response = client.head(EPISODE)
    assert response.status_code == 200
    assert response.headers["Content-Length"] == str(len(AUDIO))
    assert response.data == b""


def test_missing_episode_is_404(client):
    assert client.get(f"/feed/{TOKEN}/episodes/nope.mp3").status_code == 404


@pytest.mark.parametrize(
    "path",
    [
        "/feed/wrong-token/feed.xml",
        "/feed/wrong-token/episodes/test-episode.mp3",
        "/feed/feed.xml",
        "/feed//feed.xml",
        "/feed/episodes/test-episode.mp3",
        "/",
        "/feed",
        f"/feed/{TOKEN}",
        f"/feed/{TOKEN}/other.xml",
        f"/feed/{TOKEN}/episodes/",
        f"/feed/{TOKEN}/episodes/..%2Ftest-episode.mp3",
        "/robots.txt",
        "/static/x",
    ],
)
def test_every_other_address_gives_the_same_404(client, path):
    reference = client.get("/nothing-here")
    response = client.get(path)
    assert response.status_code == 404
    assert response.data == reference.data
    assert dict(response.headers) == dict(reference.headers)


@pytest.mark.parametrize(
    "path", [FEED, EPISODE, "/feed/wrong/feed.xml", "/nothing-here", "/static/x"]
)
@pytest.mark.parametrize("method", ["post", "put", "delete", "patch", "options"])
def test_other_methods_give_the_same_404(client, path, method):
    reference = client.get("/nothing-here")
    response = getattr(client, method)(path)
    assert response.status_code == 404
    assert response.data == reference.data
    assert dict(response.headers) == dict(reference.headers)
    assert "Allow" not in response.headers


def test_wrong_token_does_not_touch_the_bucket(bucket):
    from linkcast.app import Config, create_app
    from linkcast.storage import AudioStorage

    class Exploding(AudioStorage):
        def list_episodes(self):
            raise AssertionError("bucket read without a valid token")

        def get_size(self, name):
            raise AssertionError("bucket read without a valid token")

    config = Config(feed_token=TOKEN, audio_bucket="b")
    client = create_app(config, Exploding(bucket, "test/")).test_client()
    assert client.get("/feed/x/feed.xml").status_code == 404
    assert client.get("/feed/x/episodes/test-episode.mp3").status_code == 404


def test_one_log_line_per_request_without_path_or_token(client, caplog):
    caplog.set_level(logging.INFO, logger="linkcast")
    client.get(FEED, headers={"User-Agent": "Castamatic/1.0"})
    client.get(EPISODE, headers={"Range": "bytes=0-9"})
    client.get(f"/feed/wrong-{TOKEN}/feed.xml")
    client.get("/secret-looking-path")
    lines = [r.getMessage() for r in caplog.records if r.name == "linkcast"]
    assert len(lines) == 4
    assert "route=feed status=200" in lines[0] and "user_agent=Castamatic/1.0" in lines[0]
    assert "route=episode status=206 size=10" in lines[1]
    assert "route=feed status=404" in lines[2]
    assert "route=other status=404" in lines[3]
    everything = "\n".join(lines) + caplog.text
    for forbidden in (TOKEN, "wrong-", "secret-looking-path", "test-episode", "/feed/"):
        assert forbidden not in everything


def test_log_line_survives_odd_user_agent(client, caplog):
    caplog.set_level(logging.INFO, logger="linkcast")
    client.get(FEED, headers={"User-Agent": "bad\x01agent\N{LATIN SMALL LETTER E WITH ACUTE}" + "x" * 500})
    line = caplog.records[-1].getMessage()
    assert "\n" not in line and len(line) < 400


def _client_with(bucket, **attrs):
    from linkcast.app import Config, create_app
    from linkcast.storage import AudioStorage

    cls = type("Broken", (AudioStorage,), attrs)
    config = Config(feed_token=TOKEN, audio_bucket="b")
    return create_app(config, cls(bucket, "test/")).test_client()


def _boom(*_args, **_kwargs):
    raise RuntimeError(f"failure for /feed/{TOKEN}/feed.xml")


def _assert_clean(caplog, response):
    everything = caplog.text + response.get_data(as_text=True)
    assert TOKEN not in everything
    assert "/feed/" not in everything
    assert "RuntimeError" in caplog.text


@pytest.mark.parametrize(
    "attr, path",
    [("list_episodes", FEED), ("get_size", EPISODE)],
)
def test_storage_error_logs_no_path_or_token(bucket, caplog, attr, path):
    caplog.set_level(logging.INFO)
    client = _client_with(bucket, **{attr: _boom})
    response = client.get(path)
    assert response.status_code == 500
    _assert_clean(caplog, response)


def test_error_while_streaming_logs_no_path_or_token(bucket, caplog, monkeypatch):
    from linkcast.storage import AudioStorage

    caplog.set_level(logging.INFO)
    monkeypatch.setattr("linkcast.storage.CHUNK_SIZE", 100)
    calls = []

    def flaky(self, name, start, end):
        calls.append(start)
        if len(calls) > 1:
            raise RuntimeError(f"failure for /feed/{TOKEN}/episodes/{name}.mp3")
        return b"x" * (end - start + 1)

    client = _client_with(bucket, read_range=flaky)
    response = client.get(EPISODE)
    _assert_clean(caplog, response)
    assert len(response.data) == 100


def test_error_on_the_first_chunk_logs_no_path_or_token(bucket, caplog):
    caplog.set_level(logging.INFO)

    def broken(self, name, start, end):
        raise RuntimeError(f"failure for /feed/{TOKEN}/episodes/{name}.mp3")

    client = _client_with(bucket, read_range=broken)
    response = client.get(EPISODE)
    _assert_clean(caplog, response)
    assert response.data == b""


@pytest.mark.parametrize("path", ["/feed/wrong/feed.xml", "/nothing-here", "/static/x"])
def test_head_on_a_wrong_address_gives_the_same_404_headers(client, path):
    reference = client.get("/nothing-here")
    response = client.head(path)
    assert response.status_code == 404
    assert dict(response.headers) == dict(reference.headers)
