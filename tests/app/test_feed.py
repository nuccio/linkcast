from datetime import datetime, timezone
from xml.etree import ElementTree as ET

from linkcast.feed import ITUNES_NS, build_feed
from linkcast.storage import Episode


def test_feed_content():
    episodes = [Episode("one", 123, datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc))]
    root = ET.fromstring(build_feed(episodes, "https://example.test", "TOKEN"))
    channel = root.find("channel")
    assert channel.find("title").text == "LinkCast (test)"
    assert channel.find(f"{{{ITUNES_NS}}}block").text == "Yes"
    item = channel.find("item")
    assert item.find("title").text == "one"
    assert item.find("pubDate").text == "Sun, 01 Nov 2026 10:00:00 GMT"
    enclosure = item.find("enclosure")
    assert enclosure.get("url") == "https://example.test/feed/TOKEN/episodes/one.mp3"
    assert enclosure.get("length") == "123"
    assert enclosure.get("type") == "audio/mpeg"


def test_empty_feed_is_valid():
    root = ET.fromstring(build_feed([], "https://example.test", "TOKEN"))
    assert root.find("channel").findall("item") == []
