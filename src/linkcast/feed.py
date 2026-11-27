"""The RSS feed of the episodes."""

from collections.abc import Iterable
from email.utils import format_datetime
from xml.etree import ElementTree as ET

from linkcast.storage import Episode

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ET.register_namespace("itunes", ITUNES_NS)

FEED_TITLE = "LinkCast (test)"
FEED_DESCRIPTION = "Private test feed of LinkCast."


def build_feed(episodes: Iterable[Episode], base_url: str, token: str) -> bytes:
    """Build the RSS document.

    ``base_url`` is ``https://<host>`` as seen in the request. Each enclosure
    carries the same token as the feed address.
    """
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = FEED_TITLE
    ET.SubElement(channel, "description").text = FEED_DESCRIPTION
    ET.SubElement(channel, "language").text = "it"
    ET.SubElement(channel, f"{{{ITUNES_NS}}}block").text = "Yes"
    for episode in episodes:
        url = f"{base_url}/feed/{token}/episodes/{episode.name}.mp3"
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = episode.name
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = episode.name
        ET.SubElement(item, "pubDate").text = format_datetime(episode.created, usegmt=True)
        ET.SubElement(
            item, "enclosure", {"url": url, "length": str(episode.size), "type": "audio/mpeg"}
        )
    return ET.tostring(rss, encoding="utf-8", xml_declaration=True)
