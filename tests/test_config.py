"""Tests de la configuration (aucune dépendance QGIS — exécutables partout)."""

import pytest

from common.config import ConfigError, load_settings, parse_env_file


def test_parse_env_file_ignores_comments_and_blanks(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        '# commentaire\n\nTERANGA_LLM_PROVIDER=gemini\nGEMINI_API_KEY="sk-test-123"\n',
        encoding="utf-8",
    )
    values = parse_env_file(env)
    assert values["TERANGA_LLM_PROVIDER"] == "gemini"
    assert values["GEMINI_API_KEY"] == "sk-test-123"


def test_parse_env_file_missing_file(tmp_path):
    assert parse_env_file(tmp_path / "absent.env") == {}


def test_defaults_without_env_file(tmp_path):
    settings = load_settings(tmp_path / "absent.env")
    assert settings.provider == "openrouter"
    assert settings.base_url == "https://openrouter.ai/api/v1"
    assert settings.max_retries == 2
    assert settings.timeout == 60
    assert settings.is_ready is False


def test_env_file_values_are_used(tmp_path):
    env = tmp_path / ".env"
    env.write_text(
        "TERANGA_LLM_PROVIDER=gemini\nGEMINI_API_KEY=cle-de-test\nTERANGA_LLM_TIMEOUT=30\n",
        encoding="utf-8",
    )
    settings = load_settings(env)
    assert settings.provider == "gemini"
    assert settings.api_key == "cle-de-test"
    assert settings.model == "gemini-2.0-flash"
    assert settings.timeout == 30
    assert settings.is_ready is True


def test_os_environment_overrides_file(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("TERANGA_LLM_PROVIDER=gemini\nGEMINI_API_KEY=du-fichier\n", encoding="utf-8")
    monkeypatch.setenv("GEMINI_API_KEY", "de-lenvironnement")
    settings = load_settings(env)
    assert settings.api_key == "de-lenvironnement"


def test_unknown_provider_raises(tmp_path):
    env = tmp_path / ".env"
    env.write_text("TERANGA_LLM_PROVIDER=autre\ncle=1\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_settings(env)


def test_invalid_integer_raises(tmp_path):
    env = tmp_path / ".env"
    env.write_text("TERANGA_LLM_TIMEOUT=abc\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_settings(env)
