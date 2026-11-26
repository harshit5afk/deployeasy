import io
import json
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from app.render_client import get_render_service_environment


def _response(page):
    return io.BytesIO(json.dumps(page).encode("utf-8"))


def test_get_render_service_environment_fetches_all_cursor_pages():
    pages = [
        _response([
            {"cursor": "cursor-one", "envVar": {"key": "TOKEN", "value": "first-secret"}},
        ]),
        _response([
            {"cursor": "cursor-two", "envVar": {"key": "PORT", "value": "8080"}},
        ]),
        _response([]),
    ]

    with patch("app.render_client.config.RENDER_API_KEY", "render-api-key"):
        with patch("app.render_client.urllib.request.urlopen", side_effect=pages) as urlopen:
            variables = get_render_service_environment("srv-example")

    assert variables == {"TOKEN": "first-secret", "PORT": "8080"}
    assert urlopen.call_count == 3
    first_request = urlopen.call_args_list[0].args[0]
    second_request = urlopen.call_args_list[1].args[0]
    assert parse_qs(urlparse(first_request.full_url).query) == {"limit": ["100"]}
    assert parse_qs(urlparse(second_request.full_url).query) == {
        "limit": ["100"],
        "cursor": ["cursor-one"],
    }
