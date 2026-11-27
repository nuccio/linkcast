"""The Flask application: two token-protected routes and one log line per request."""

import logging
import os
import re
import sys
from dataclasses import dataclass

from flask import Flask, Response, request

from linkcast.feed import build_feed
from linkcast.storage import AudioStorage, is_valid_name
from linkcast.token import token_matches, validate_token

logger = logging.getLogger("linkcast")

DEFAULT_PREFIX = "test/"
DEFAULT_PORT = 8080


@dataclass(frozen=True)
class Config:
    feed_token: str
    audio_bucket: str
    audio_prefix: str = DEFAULT_PREFIX
    port: int = DEFAULT_PORT

    @classmethod
    def from_env(cls, environ=None) -> "Config":
        environ = os.environ if environ is None else environ
        bucket = environ.get("AUDIO_BUCKET", "")
        if not bucket:
            raise ValueError("AUDIO_BUCKET is required")
        prefix = environ.get("AUDIO_PREFIX") or DEFAULT_PREFIX
        if not prefix.endswith("/"):
            prefix += "/"
        return cls(
            feed_token=validate_token(environ.get("FEED_TOKEN")),
            audio_bucket=bucket,
            audio_prefix=prefix,
            port=int(environ.get("PORT") or DEFAULT_PORT),
        )


def _clean(value: str, limit: int = 200) -> str:
    """Make a header value safe for a one-line log."""
    return re.sub(r"[^\x20-\x7e]", "?", value)[:limit]


def _not_found() -> Response:
    return Response("Not Found\n", status=404, mimetype="text/plain")


def create_app(config: Config | None = None, storage: AudioStorage | None = None) -> Flask:
    """Create the application; ``config`` and ``storage`` are injected by the tests."""
    config = config or Config.from_env()
    storage = storage or AudioStorage.from_bucket_name(config.audio_bucket, config.audio_prefix)
    if not logger.handlers and not logging.getLogger().handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    app = Flask(__name__)

    def authorized(token: str) -> bool:
        return token_matches(token, config.feed_token)

    @app.get("/feed/<token>/feed.xml", endpoint="feed")
    def feed(token: str):
        if not authorized(token):
            return _not_found()
        body = build_feed(storage.list_episodes(), f"https://{request.host}", token)
        return Response(body, mimetype="application/rss+xml")

    @app.get("/feed/<token>/episodes/<name>.mp3", endpoint="episode")
    def episode(token: str, name: str):
        if not authorized(token) or not is_valid_name(name):
            return _not_found()
        size = storage.get_size(name)
        if size is None:
            return _not_found()
        headers = {"Accept-Ranges": "bytes"}
        byte_range = request.range
        start, end, status = 0, size - 1, 200
        if byte_range is not None and byte_range.units == "bytes":
            bounds = byte_range.range_for_length(size)
            if bounds is None or size == 0:
                headers["Content-Range"] = f"bytes */{size}"
                return Response(status=416, headers=headers)
            start, end = bounds[0], bounds[1] - 1
            status = 206
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        headers["Content-Length"] = str(max(end - start + 1, 0))
        if request.method == "HEAD" or size == 0:
            return Response(status=status, mimetype="audio/mpeg", headers=headers)
        return Response(
            storage.iter_range(name, start, end),
            status=status,
            mimetype="audio/mpeg",
            headers=headers,
            direct_passthrough=True,
        )

    # Every other address, and a method other than GET or HEAD on a valid
    # one, gets the same 404, so nothing tells a stranger the address exists.
    @app.errorhandler(404)
    @app.errorhandler(405)
    def not_found(_error):
        return _not_found()

    @app.after_request
    def finish(response: Response) -> Response:
        response.headers["X-Robots-Tag"] = "noindex"
        # Route name, status, size and user agent only: never the path or the token.
        route = request.endpoint if request.endpoint in ("feed", "episode") else "other"
        size = response.headers.get("Content-Length", "-")
        agent = _clean(request.headers.get("User-Agent", "-"))
        logger.info("request route=%s status=%d size=%s user_agent=%s", route, response.status_code, size, agent)
        return response

    return app
