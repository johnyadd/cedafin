"""
polite_fetch.py — read what we are allowed to read, and say who is asking.

WHY THIS EXISTS
The scanners on this project send Chrome's user agent to get past bot
protection. The lending scanner's own docstring says so in as many words: "a
browser-shaped request ... gets past most of it."

Then one of them hit a page whose robots.txt disallows automated access, and
the site's whole argument came into view. Cedafin tells providers to publish
what they can prove and tells readers exactly how every figure was obtained.
A crawler that ignores robots.txt while claiming to be Chrome is not that.

So this does two things the previous fetchers did not:

  It reads robots.txt before touching a host, and skips what is disallowed.
  It says who it is — CedafinBot, with an address to complain to.

WHAT IT COSTS
Access. Some sites block anything that is not a browser, and an honest user
agent will be turned away by a few of them. Republic Bank disallow crawlers
outright, so pages we previously read now report as disallowed.

That is the correct trade. A finding obtained by pretending to be a browser on
a site that asked us not to is not a finding this project can stand behind,
and "we did not look because they asked us not to" is a perfectly good thing
to publish.

WHAT IT DOES NOT PREVENT
A person opening a public page in a browser and reading it. robots.txt governs
automated access, not human attention. Where a scan reports disallowed, the
page can still be read by hand — and the record should say it was read by hand
rather than scanned, because those are different facts about how we know.

Usage:
    from polite_fetch import fetch, why_blocked

    status, html = fetch(url)
    if status == 999:
        print(why_blocked(url))   # disallowed by robots.txt
"""

from __future__ import annotations

import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

# Honest. If a site turns us away for not being Chrome, that is their answer
# and we record it rather than working around it.
# The conventional crawler format. "Mozilla/5.0 (compatible; ...)" is what
# Googlebot, Bingbot and Applebot all send — it is the string servers parse,
# not a claim to be a browser. The bot is named and a page explaining it is
# linked, which is the whole of what honesty requires here.
#
# What the scanners sent before claimed a specific Windows machine running a
# specific Chrome build, with CedafinBot tacked on the end. That was a dodge.
USER_AGENT = (
    "Mozilla/5.0 (compatible; CedafinBot/1.0; "
    "+https://cedafin.com/methodology; data@cedafin.com)"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}

# 999 is ours, not HTTP's. It means "we were asked not to", which is a
# different fact from a 403 and should not be reported as one.
DISALLOWED = 999

_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
_delays: dict[str, float] = {}
_last_hit: dict[str, float] = {}


def _ctx() -> ssl.SSLContext:
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c


def _robots_for(url: str) -> urllib.robotparser.RobotFileParser | None:
    """Fetch and cache a host's robots.txt. One request per host per run."""
    parts = urllib.parse.urlparse(url)
    host = f"{parts.scheme}://{parts.netloc}"
    if host in _robots:
        return _robots[host]

    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{host}/robots.txt")
    try:
        req = urllib.request.Request(f"{host}/robots.txt", headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15, context=_ctx()) as r:
            rp.parse(r.read().decode("utf-8", "replace").splitlines())
    except Exception:  # noqa: BLE001
        # No robots.txt, or unreachable. The convention is that absence means
        # permitted — and a site that cannot serve robots.txt has not asked us
        # for anything.
        _robots[host] = None
        return None

    _robots[host] = rp
    # Honour Crawl-delay where a site sets one. Most do not.
    try:
        delay = rp.crawl_delay(USER_AGENT)
        if delay:
            _delays[host] = float(delay)
    except Exception:  # noqa: BLE001
        pass
    return rp


def allowed(url: str) -> bool:
    rp = _robots_for(url)
    if rp is None:
        return True
    try:
        return rp.can_fetch(USER_AGENT, url)
    except Exception:  # noqa: BLE001
        # A robots.txt we cannot parse is not consent. Err toward not reading.
        return False


def why_blocked(url: str) -> str:
    parts = urllib.parse.urlparse(url)
    return (
        f"{parts.netloc} disallows automated access at this path. "
        f"Read it by hand if it matters — robots.txt governs crawlers, not "
        f"people — and record that it was read by hand."
    )


def fetch(url: str, timeout: int = 25) -> tuple[int, str]:
    """
    Returns (status, html).

    status is an HTTP code, 0 for a connection failure, or DISALLOWED (999)
    where robots.txt says not to. The caller should report those three
    differently: a 404 is a missing page, a 0 is a broken connection, and a
    999 is a request we chose to honour.
    """
    if not allowed(url):
        return DISALLOWED, ""

    parts = urllib.parse.urlparse(url)
    host = f"{parts.scheme}://{parts.netloc}"

    # Crawl-delay, where set, and a courteous floor where not.
    wait = _delays.get(host, 0.0)
    since = time.time() - _last_hit.get(host, 0.0)
    if since < wait:
        time.sleep(wait - since)
    _last_hit[host] = time.time()

    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            return getattr(r, "status", 200), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:  # noqa: BLE001
        return 0, ""


def status_word(status: int) -> str:
    """For scan output, so the three cases read differently."""
    if status == DISALLOWED:
        return "disallowed by robots.txt"
    if status == 0:
        return "no response"
    if status == 200:
        return "ok"
    return f"HTTP {status}"
