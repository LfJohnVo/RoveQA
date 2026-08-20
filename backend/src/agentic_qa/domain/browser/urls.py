"""Turning a URL into something safe to keep.

Applications put credentials in URLs. A password-reset link, a signed download, a
session token forwarded as a query parameter — all normal, all things a QA agent walks
past. The danger is not reading them; it is *keeping* them, because what this system
keeps outlives the session that issued the token: a state map is compared night after
night, and an observation travels into a prompt and a report.

So there are two kinds of URL here and the distinction is deliberate:

- **A URL to act on** keeps everything, because `/records?status=open` is a different
  page from `/records` and an explorer that dropped the query would navigate somewhere
  else. These live as long as the run does — the same lifetime as the session whose
  token they might carry.
- **A URL to keep** is stripped to scheme, host and path. That is exactly what identity
  and reporting need, and nothing a credential can hide in.
"""

from urllib.parse import urlsplit


def safe_url(url: str) -> str:
    """Scheme, host and path. No query, no fragment, no userinfo.

    Query strings and fragments are where tokens ride, and `user:password@host` is a
    credential in the authority itself. A URL that cannot be parsed comes back empty
    rather than partially cleaned: half-sanitised is the worst of both.
    """
    if not url:
        return ""
    parts = urlsplit(url.strip())
    if not parts.scheme or not parts.hostname:
        # Not a URL we can reason about — `about:blank`, a bare path, something
        # malformed. Passing it through would mean guessing which part is sensitive.
        return url if "://" not in url and "@" not in url and "?" not in url else ""
    port = f":{parts.port}" if parts.port is not None else ""
    return f"{parts.scheme}://{parts.hostname}{port}{parts.path}"
