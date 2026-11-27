import pytest

from linkcast.app import Config
from linkcast.token import token_matches, validate_token


def test_accepts_a_long_token():
    assert validate_token("a" * 32) == "a" * 32


@pytest.mark.parametrize("value", [None, "", "short", "a" * 31])
def test_refuses_a_short_or_missing_token(value):
    with pytest.raises(ValueError):
        validate_token(value)


def test_error_message_does_not_contain_the_token():
    with pytest.raises(ValueError) as error:
        validate_token("secret-short")
    assert "secret-short" not in str(error.value)


def test_matches_only_the_same_token():
    assert token_matches("a" * 40, "a" * 40)
    assert not token_matches("a" * 39 + "b", "a" * 40)
    assert not token_matches("", "a" * 40)


def test_non_ascii_candidate_does_not_raise():
    assert not token_matches("é" * 40, "a" * 40)


def test_service_refuses_to_start_with_a_short_token():
    with pytest.raises(ValueError):
        Config.from_env({"FEED_TOKEN": "x" * 31, "AUDIO_BUCKET": "b"})


def test_config_defaults_and_values():
    config = Config.from_env({"FEED_TOKEN": "x" * 32, "AUDIO_BUCKET": "b"})
    assert config.audio_prefix == "test/"
    assert config.port == 8080
    config = Config.from_env(
        {"FEED_TOKEN": "x" * 32, "AUDIO_BUCKET": "b", "AUDIO_PREFIX": "eps", "PORT": "9000"}
    )
    assert config.audio_prefix == "eps/"
    assert config.port == 9000


def test_config_requires_a_bucket():
    with pytest.raises(ValueError):
        Config.from_env({"FEED_TOKEN": "x" * 32})
