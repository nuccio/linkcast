"""The Flask application: two token-protected routes and one log line per request."""

import logging
import os
import re
import sys
from dataclasses import dataclass
from urllib.parse import quote

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


# "/feed/<segment>" with repeated slashes, an encoded slash and any case; the
# segment ends at a slash, an encoded slash, a quote, a space or a query.
_FEED_SEGMENT = re.compile(
    r"/+feed(?:/|%2f)+(?:(?!%2f)[^/\s'\"?])+",
    re.IGNORECASE,
)


class RedactFeedPath(logging.Filter):
    """Redact the feed token in a log record, message and arguments.

    The literal token (plain and percent-encoded) is replaced wherever it is,
    and so is the segment after ``/feed/`` whatever it holds.
    """

    def __init__(self, token: str = ""):
        super().__init__()
        self._literals = [t for t in {token, quote(token, safe="")} if t]

    def _redact(self, value):
        if not isinstance(value, str):
            return value
        for literal in self._literals:
            value = value.replace(literal, "<redacted>")
        return _FEED_SEGMENT.sub("/feed/<redacted>", value)

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = self._redact(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(self._redact(a) for a in record.args)
        elif isinstance(record.args, dict):
            record.args = {k: self._redact(v) for k, v in record.args.items()}
        return True


class _App(Flask):
    """Flask whose error log never contains the request path (it holds the token)."""

    def log_exception(self, exc_info):
        route = request.endpoint if request.endpoint in ("feed", "episode") else "other"
        logger.error("error route=%s exception=%s", route, exc_info[0].__name__)


def _guarded(chunks, route: str):
    """Yield the chunks; if reading fails, log without path or token and stop."""
    try:
        yield from chunks
    except Exception as error:
        logger.error("error route=%s exception=%s", route, type(error).__name__)


def create_app(config: Config | None = None, storage: AudioStorage | None = None) -> Flask:
    """Create the application; ``config`` and ``storage`` are injected by the tests."""
    config = config or Config.from_env()
    storage = storage or AudioStorage.from_bucket_name(config.audio_bucket, config.audio_prefix)
    if not logger.handlers and not logging.getLogger().handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    gunicorn_error = logging.getLogger("gunicorn.error")
    for old in [f for f in gunicorn_error.filters if isinstance(f, RedactFeedPath)]:
        gunicorn_error.removeFilter(old)
    gunicorn_error.addFilter(RedactFeedPath(config.feed_token))

    app = _App(__name__, static_folder=None)
    # No redirect for a doubled slash: it would answer before the token check.
    app.url_map.merge_slashes = False

    def authorized(token: str) -> bool:
        return token_matches(token, config.feed_token)

    @app.get("/feed/<token>/feed.xml", endpoint="feed", provide_automatic_options=False)
    def feed(token: str):
        if not authorized(token):
            return _not_found()
        body = build_feed(storage.list_episodes(), f"https://{request.host}", token)
        return Response(body, mimetype="application/rss+xml")

    @app.get(
        "/feed/<token>/episodes/<name>.mp3", endpoint="episode", provide_automatic_options=False
    )
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
            _guarded(storage.iter_range(name, start, end), "episode"),
            status=status,
            mimetype="audio/mpeg",
            headers=headers,
            direct_passthrough=True,
        )

    # Every other address, and a method other than GET or HEAD on a valid
    # one, gets the same 404, so nothing tells a stranger the address exists.
    @app.errorhandler(500)
    def server_error(_error):
        return Response("Internal Server Error\n", status=500, mimetype="text/plain")

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
