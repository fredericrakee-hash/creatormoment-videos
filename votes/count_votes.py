"""Count story votes from Instagram comments (account: shortsfilm).

Runs on GitHub Actions. Needs the secret IG_TOKEN (long-lived Instagram User
access token, Instagram API with Instagram Login, scopes instagram_business_basic
+ instagram_business_manage_comments).

How a post declares its vote: the caption contains a line like
    VOTE: DOOR / TUNNEL
(2-4 options, separated by "/"). Comments are matched against the option words
and against the letters A, B, C, D (A = first option, ...).

Rules:
- A comment counts only if it names exactly one option.
- One vote per person: the latest comment of a user wins.
- Only counts are written to votes/results/<media_id>.json. No usernames, no
  comment texts are stored.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://graph.instagram.com"
TOKEN = os.environ.get("IG_TOKEN", "").strip()
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
RECENT_POSTS = 5


def get(url, params=None):
    if params is not None:
        params = dict(params, access_token=TOKEN)
        url = url + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def paged(url, params):
    data = get(url, params)
    while True:
        for item in data.get("data", []):
            yield item
        nxt = data.get("paging", {}).get("next")
        if not nxt:
            break
        data = get(nxt)


def parse_options(caption):
    m = re.search(r"^\s*VOTE\s*:\s*(.+)$", caption or "", re.I | re.M)
    if not m:
        return None
    opts = [o.strip() for o in m.group(1).split("/") if o.strip()]
    return opts if 2 <= len(opts) <= 4 else None


def classify(text, options):
    t = (text or "").upper()
    letters = "ABCD"[: len(options)]
    hits = set()
    for i, opt in enumerate(options):
        word = re.escape(opt.upper())
        if re.search(r"(?<![A-Z0-9])" + word + r"(?![A-Z0-9])", t):
            hits.add(i)
    # single letters ("A", "b!", "Definitely B") only in short comments,
    # so "A great video" is not a vote
    words = re.findall(r"[A-Z0-9']+", t)
    for i, L in enumerate(letters if len(words) <= 3 else ""):
        if re.search(r"(?<![A-Z0-9'])" + L + r"(?![A-Z0-9'])", t):
            hits.add(i)
    if "🅰" in (text or ""):
        hits.add(0)
    if "🅱" in (text or ""):
        hits.add(1)
    return hits.pop() if len(hits) == 1 else None


def refresh_token():
    """Extends the current long-lived token by another 60 days."""
    try:
        res = get(API + "/refresh_access_token", {"grant_type": "ig_refresh_token"})
        days = int(res.get("expires_in", 0)) // 86400
        print(f"token refreshed, valid for ~{days} days")
        return days
    except Exception as e:  # noqa: BLE001
        print(f"::warning::token refresh failed: {e}")
        return None


def main():
    if not TOKEN:
        print("::error::secret IG_TOKEN is missing")
        sys.exit(1)
    os.makedirs(OUT, exist_ok=True)
    if "--refresh" in sys.argv:
        if refresh_token() is None:
            sys.exit(1)
        return

    media = get(API + "/me/media", {
        "fields": "id,caption,timestamp,permalink,comments_count",
        "limit": RECENT_POSTS,
    }).get("data", [])

    summary = []
    for m in media:
        options = parse_options(m.get("caption"))
        if not options:
            continue
        latest = {}  # user -> (timestamp, option or None); kept in memory only
        total = 0
        for c in paged(f"{API}/{m['id']}/comments",
                       {"fields": "id,text,timestamp,username", "limit": 50}):
            total += 1
            user = c.get("username") or c.get("id")
            ts = c.get("timestamp", "")
            choice = classify(c.get("text"), options)
            if choice is None:
                continue
            if user not in latest or ts > latest[user][0]:
                latest[user] = (ts, choice)
        counts = [0] * len(options)
        for _, choice in latest.values():
            counts[choice] += 1
        best = max(counts) if counts else 0
        leaders = [options[i] for i, n in enumerate(counts) if n == best]
        result = {
            "media_id": m["id"],
            "permalink": m.get("permalink"),
            "posted": m.get("timestamp"),
            "options": options,
            "votes": dict(zip(options, counts)),
            "valid_votes": sum(counts),
            "comments_total": total,
            "winner": leaders[0] if len(leaders) == 1 and best > 0 else None,
            "tie": len(leaders) > 1 and best > 0,
            "counted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        path = os.path.join(OUT, f"{m['id']}.json")
        old = None
        if os.path.exists(path):
            with open(path) as f:
                old = json.load(f)
        if old and {k: v for k, v in old.items() if k != "counted_at"} == \
                {k: v for k, v in result.items() if k != "counted_at"}:
            result["counted_at"] = old["counted_at"]  # unchanged -> no new commit
        with open(path, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        summary.append(result)
        print(f"{m.get('permalink')}: {result['votes']} (winner: {result['winner']})")

    with open(os.path.join(OUT, "latest.json"), "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    if not summary:
        print("no post with a 'VOTE:' line among the latest posts")


if __name__ == "__main__":
    main()
