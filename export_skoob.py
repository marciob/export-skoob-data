#!/usr/bin/env python3
"""Export your entire Skoob library to JSON.

Zero dependencies — Python 3.8+ standard library only.

It reads your Skoob API token from the SKOOB_JWT environment variable
(or a local .env file), then dumps every shelf across every media type,
paginating fully, and writes:

  output/raw/{type}__{filter}.json  one file per shelf (exactly what the
                                    bookshelf API returns)
  output/books.json                 merged, de-duplicated library, each
                                    book tagged with the shelves it's on

No personal data is stored in this repository. See README.md for how to
obtain your token (it lives in an HttpOnly cookie, so you copy it from
your browser's console once; it expires ~15 days after issue).
"""
from __future__ import annotations

import base64
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://prd-api.skoob.com.br/api/v1/bookshelf"
# Skoob's edge/WAF rejects the default "Python-urllib" agent with HTTP 403,
# so we present a normal browser User-Agent (same request a browser makes).
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "output")
RAW = os.path.join(OUT, "raw")
LIMIT = 100

# Media types and shelf filters, taken from Skoob's own bookshelf sidebar.
# Skoob's API currently only accepts these two; other values (e.g. "comic",
# "manga") are rejected with HTTP 400 "must be equal to one of the allowed
# values".
BOOKSHELF_TYPES = ["book", "magazine"]
FILTERS = [
    "all", "read", "reading", "want_to_read", "rereading", "abandoned",
    "favorited", "desired", "rated", "reviewed", "owned", "lent",
    "reading_goal", "ebook", "audiobook",
]


def load_dotenv(path: str) -> None:
    """Minimal .env loader (no dependency). Does not overwrite real env vars."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            os.environ.setdefault(key, val)


def jwt_payload(token: str) -> dict:
    """Decode (not verify) the JWT payload to read `id` and `exp`."""
    try:
        part = token.split(".")[1]
        part += "=" * (-len(part) % 4)
        return json.loads(base64.urlsafe_b64decode(part))
    except Exception:
        return {}


def get_token() -> str:
    token = os.environ.get("SKOOB_JWT", "").strip()
    if not token:
        sys.exit(
            "ERROR: SKOOB_JWT is not set.\n"
            "Copy .env.example to .env and paste your token, or run:\n"
            '  SKOOB_JWT="eyJ..." python3 export_skoob.py\n'
            "See README.md -> \"Getting your Skoob token\"."
        )
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    return token


def api_get(url: str, token: str, retries: int = 3) -> dict | None:
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": token,
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                sys.exit(
                    f"ERROR: Skoob rejected the request (HTTP {exc.code}). "
                    "Most likely the token expired (~15-day TTL) — grab a "
                    "fresh one (README.md). If it's brand new, Skoob's edge "
                    "may be blocking your network."
                )
            if 400 <= exc.code < 500:
                # client error (bad param, not found) — retrying won't help
                print(f"  ! HTTP {exc.code} on {url}", file=sys.stderr)
                return None
            if attempt == retries:
                print(f"  ! HTTP {exc.code} on {url}", file=sys.stderr)
                return None
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == retries:
                print(f"  ! network error on {url}: {exc}", file=sys.stderr)
                return None
        time.sleep(1.5 * attempt)
    return None


def fetch_shelf(btype: str, filt: str, user_id: str, token: str) -> dict:
    items: list[dict] = []
    total_items = 0
    page = 1
    while True:
        url = (
            f"{API}?page={page}&limit={LIMIT}&bookshelf_type={btype}"
            f"&user_id={user_id}&filter={filt}&search_type=title"
        )
        data = api_get(url, token)
        if not isinstance(data, dict):
            break
        total_items = data.get("total_items", total_items) or 0
        batch = data.get("items") or []
        items.extend(batch)
        if len(batch) < LIMIT:
            break
        page += 1
    return {
        "bookshelf_type": btype,
        "filter": filt,
        "total_items": total_items,
        "collected": len(items),
        "items": items,
    }


def merge(shelves: list[dict], user_id: str) -> dict:
    """De-duplicate by edition_id (fallback book_id); tag shelf membership.

    `filter=all` is the master library list, recorded as `in_library`
    rather than as a user shelf. Shelves are not mutually exclusive.
    """
    books: dict = {}
    shelf_counts: dict = {}
    for sh in shelves:
        btype, filt = sh["bookshelf_type"], sh["filter"]
        shelf_counts[f"{btype}/{filt}"] = len(sh["items"])
        for it in sh["items"]:
            key = it.get("edition_id") or it.get("book_id")
            if key is None:
                continue
            rec = books.get(key)
            if rec is None:
                rec = dict(it)
                rec["bookshelf_types"] = set()
                rec["shelves"] = set()
                rec["in_library"] = False
                books[key] = rec
            rec["bookshelf_types"].add(btype)
            if filt == "all":
                rec["in_library"] = True
            else:
                rec["shelves"].add(filt)

    merged = []
    for rec in books.values():
        rec["bookshelf_types"] = sorted(rec["bookshelf_types"])
        rec["shelves"] = sorted(rec["shelves"])
        merged.append(rec)
    merged.sort(key=lambda r: ((r.get("title") or "").lower(),
                               (r.get("author") or "").lower()))
    return {
        "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": "skoob.com.br /api/v1/bookshelf",
        "user_id": user_id,
        "unique_books": len(merged),
        "shelf_counts": dict(sorted(shelf_counts.items())),
        "books": merged,
    }


def main() -> None:
    load_dotenv(os.path.join(ROOT, ".env"))
    token = get_token()

    payload = jwt_payload(token)
    user_id = os.environ.get("SKOOB_USER_ID", "").strip() or payload.get("id")
    if not user_id:
        sys.exit(
            "ERROR: could not determine your user_id. Either the token is "
            "malformed or set SKOOB_USER_ID in .env (it's the id in your "
            "profile URL /user/{id}/bookshelf)."
        )
    exp = payload.get("exp")
    if exp:
        left = datetime.datetime.fromtimestamp(
            exp, datetime.timezone.utc
        ) - datetime.datetime.now(datetime.timezone.utc)
        days = left.total_seconds() / 86400
        if days < 0:
            sys.exit("ERROR: this token expired. Grab a fresh one (README.md).")
        print(f"Token OK — user_id {user_id}, ~{days:.1f} day(s) until expiry.")

    os.makedirs(RAW, exist_ok=True)
    shelves = []
    for btype in BOOKSHELF_TYPES:
        for filt in FILTERS:
            sh = fetch_shelf(btype, filt, user_id, token)
            shelves.append(sh)
            with open(os.path.join(RAW, f"{btype}__{filt}.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(sh, fh, ensure_ascii=False, indent=2)
            if sh["collected"]:
                print(f"  {btype:8s} {filt:14s} "
                      f"total={sh['total_items']:<5d} got={sh['collected']}")

    result = merge(shelves, user_id)
    with open(os.path.join(OUT, "books.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    print(f"\nDone. {result['unique_books']} unique books.")
    print(f"  -> output/books.json")
    print(f"  -> output/raw/  (one file per shelf)")


if __name__ == "__main__":
    main()
