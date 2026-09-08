"""
cedafin_env.py — one place that knows how to find the Supabase keys.

WHY THIS EXISTS
Every fetcher and loader in this project carries its own copy of an env()
function that reads .env.local and exits if it is missing. That worked while
everything ran by hand on one machine.

It stops working the moment anything runs unattended. .env.local is not in the
repo — it holds a service-role key and the repo is public — so a GitHub Action
has no file to read. It has environment variables, from repository secrets.

So: read .env.local when it is there, fall back to the environment when it is
not, and fail with a message that says which variable is missing rather than
"No .env.local".

WHY NOT JUST EDIT EVERY SCRIPT
Because there are sixty of them and they will drift. This is imported by the
ones that need to run on a schedule; the rest keep their own copy until they
need this.

Usage:
    from cedafin_env import supabase_config
    BASE, KEY = supabase_config()
"""

from __future__ import annotations

import os
import sys

DOTENV = ".env.local"

URL_KEYS = ("NEXT_PUBLIC_SUPABASE_URL", "SUPABASE_URL")
SERVICE_KEYS = ("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SERVICE_KEY")


def _from_dotenv() -> dict[str, str]:
    if not os.path.exists(DOTENV):
        return {}
    out: dict[str, str] = {}
    with open(DOTENV, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _first(config: dict[str, str], names: tuple[str, ...]) -> str | None:
    for n in names:
        # Environment wins over the file, so a scheduled run can override a
        # stale local copy without editing anything.
        v = os.environ.get(n) or config.get(n)
        if v:
            return v
    return None


def supabase_config() -> tuple[str, str]:
    """
    Returns (rest_base_url, service_role_key).

    Reads .env.local if present, then the environment. Exits with a message
    naming the missing variable rather than assuming a file.
    """
    config = _from_dotenv()

    url = _first(config, URL_KEYS)
    key = _first(config, SERVICE_KEYS)

    missing = []
    if not url:
        missing.append(URL_KEYS[0])
    if not key:
        missing.append(SERVICE_KEYS[0])

    if missing:
        where = f"{DOTENV} or the environment" if os.path.exists(DOTENV) else "the environment"
        print(f"Missing {', '.join(missing)} — looked in {where}.")
        print()
        print("Running locally: check .env.local is in the working directory.")
        print("Running in CI: check the repository secrets are set and passed")
        print("through as env: in the workflow step.")
        sys.exit(1)

    return url.rstrip("/") + "/rest/v1", key
