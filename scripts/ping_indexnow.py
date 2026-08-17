#!/usr/bin/env python3
"""Tell IndexNow (Bing, Yandex, Seznam, Naver) that pages changed.

Bing discovers our URLs from the sitemap but rations crawling by how
important it thinks a site is, so new pages sat "discovered but not
crawled" for weeks. IndexNow is the push channel: we announce a change
and the engines fetch it instead of waiting for their own schedule.

Ownership is proved by hosting KEY as <KEY>.txt at the site root.

Usage:
  ping_indexnow.py --all                 every URL in sitemap.xml
  ping_indexnow.py --changed BASE HEAD   URLs whose files changed between two commits
  ping_indexnow.py https://... [...]     explicit URLs

Exits 0 even when the API is unhappy: a missed ping is not worth
failing a deploy over.
"""
import json, os, re, subprocess, sys, urllib.error, urllib.request

HOST = "keowee.club"
KEY = "8cc9f73e6c58a01ba98239a5ec5f481c"
ENDPOINT = "https://api.indexnow.org/IndexNow"
ROOT = os.path.join(os.path.dirname(__file__), "..")
# Pages the sitemap knows about; anything else is not worth announcing.
SITEMAP = os.path.join(ROOT, "sitemap.xml")


def sitemap_urls():
    try:
        xml = open(SITEMAP).read()
    except OSError:
        return []
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def changed_urls(base, head):
    """Map changed index.html files back to the URLs they serve."""
    try:
        out = subprocess.run(["git", "diff", "--name-only", base, head],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"cannot diff {base}..{head}: {e}")
        return []
    known = set(sitemap_urls())
    urls = []
    for path in out.split():
        if not path.endswith("index.html"):
            continue
        d = path[: -len("index.html")]
        url = f"https://{HOST}/" + d
        if url in known and url not in urls:
            urls.append(url)
    return urls


def submit(urls):
    if not urls:
        print("nothing to submit")
        return 0
    body = json.dumps({
        "host": HOST,
        "key": KEY,
        "keyLocation": f"https://{HOST}/{KEY}.txt",
        "urlList": urls,
    }).encode()
    req = urllib.request.Request(ENDPOINT, data=body,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"submitted {len(urls)} url(s), HTTP {r.status}")
    except urllib.error.HTTPError as e:
        # 202 = accepted, key validation pending. Anything else is informational.
        print(f"indexnow returned HTTP {e.code}: {e.read()[:200].decode(errors='replace')}")
    except Exception as e:
        print(f"indexnow unreachable, skipping: {e}")
    for u in urls:
        print("  " + u)
    return 0


def main(argv):
    if not argv or argv[0] == "--all":
        return submit(sitemap_urls())
    if argv[0] == "--changed":
        if len(argv) < 3:
            print("--changed needs BASE and HEAD")
            return 0
        return submit(changed_urls(argv[1], argv[2]))
    return submit([u for u in argv if u.startswith("http")])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
