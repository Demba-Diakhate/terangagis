"""Configuration TerangaGIS.

Sépare configuration et code (CDC V2 §18) : aucun secret dans le dépôt.
Priorité : variable d'environnement > fichier `.env` > valeur par défaut.
Aucune dépendance externe (compatible Python embarqué QGIS).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = REPO_ROOT / ".env"

PROVIDERS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "base_url_env": "OPENROUTER_BASE_URL",
        "model_env": "OPENROUTER_MODEL",
        "default_model": "",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key_env": "GEMINI_API_KEY",
        "base_url_env": "GEMINI_BASE_URL",
        "model_env": "GEMINI_MODEL",
        "default_model": "gemini-2.0-flash",
    },
}


class ConfigError(Exception):
    """Erreur de configuration levée lors du chargement des paramètres."""


@dataclass(frozen=True)
class Settings:
    provider: str
    base_url: str
    api_key: str
    model: str
    max_retries: int
    timeout: int
    step_max_retries: int = 1
    llm_backoff: float = 0.5

    @property
    def is_ready(self) -> bool:
        """Vrai si un appel LLM est possible (clé présente)."""
        return bool(self.api_key)


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse un fichier `.env` simple (KEY=VALUE, commentaires et lignes vides ignorés)."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_settings(env_file: Path | None = None) -> Settings:
    """Charge les paramètres LLM depuis l'environnement et le fichier `.env`."""
    env_path = env_file if env_file is not None else DEFAULT_ENV_FILE
    file_values = parse_env_file(env_path)

    def get(key: str, default: str = "") -> str:
        if key in os.environ and os.environ[key] != "":
            return os.environ[key]
        return file_values.get(key, default)

    provider = get("TERANGA_LLM_PROVIDER", "openrouter").lower()
    if provider not in PROVIDERS:
        raise ConfigError(
            f"Fournisseur inconnu : {provider!r}. Valeurs attendues : {sorted(PROVIDERS)}"
        )
    spec = PROVIDERS[provider]

    base_url = get(spec["base_url_env"], spec["base_url"])
    api_key = get(spec["api_key_env"], "")
    model = get(spec["model_env"], spec["default_model"])

    try:
        max_retries = int(get("TERANGA_LLM_MAX_RETRIES", "2"))
        timeout = int(get("TERANGA_LLM_TIMEOUT", "60"))
        step_max_retries = int(get("TERANGA_STEP_MAX_RETRIES", "1"))
        llm_backoff = float(get("TERANGA_LLM_BACKOFF", "0.5"))
    except ValueError as exc:
        raise ConfigError(
            "TERANGA_LLM_MAX_RETRIES, TERANGA_STEP_MAX_RETRIES et TERANGA_LLM_TIMEOUT doivent être des entiers ; "
            "TERANGA_LLM_BACKOFF un nombre"
        ) from exc

    return Settings(
        provider=provider,
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        model=model,
        max_retries=max_retries,
        timeout=timeout,
        step_max_retries=step_max_retries,
        llm_backoff=llm_backoff,
    )
