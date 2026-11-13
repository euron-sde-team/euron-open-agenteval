"""Local CLI credentials: ``agenteval-cli init`` stores an API key here, the same
convention secretguard-cli's own config.py uses, so later commands (``evaluate run``,
``compare``) do not need the password re-entered every time. An API key is revocable and
long-lived, the same credential a CI pipeline would use, created through the same
endpoint a human uses in the dashboard (POST /api/v1/orgs/{org_id}/api-keys).
"""

from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "agenteval"


def credentials_path() -> Path:
    return config_dir() / "credentials.json"


@dataclass(frozen=True, slots=True)
class Credentials:
    api_url: str
    api_key: str
    org_id: str


def save_credentials(creds: Credentials) -> None:
    path = credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"api_url": creds.api_url, "api_key": creds.api_key, "org_id": creds.org_id})
    )
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600: only the owner can read the API key


def load_credentials() -> Credentials | None:
    path = credentials_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
        return Credentials(api_url=data["api_url"], api_key=data["api_key"], org_id=data["org_id"])
    except (OSError, ValueError, KeyError):
        return None


def clear_credentials() -> None:
    path = credentials_path()
    if path.is_file():
        path.unlink()
