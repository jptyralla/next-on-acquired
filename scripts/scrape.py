#!/usr/bin/env python3
"""Scrape every Acquired episode from acquired.fm and rewrite ../data.js.

Pulls title / date / season / episode number / duration / theme colours / description
from the paginated episode list, downloads each cover (SVG or raster) and embeds it as
a data URI so the site works offline and inside a strict CSP.
"""
import base64, html, json, os, re, subprocess, tempfile, urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"}
LIST = "https://www.acquired.fm/episodes?b8478ff5_page={}"
OUT = os.path.join(os.path.dirname(__file__), "..", "data.js")
MAX_SVG = 60_000  # bigger SVGs fall back to a coloured tile

def fetch(url, binary=False):
    data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()
    return data if binary else data.decode()

def scrape_list():
    eps, page = [], 1
    while True:
        h = fetch(LIST.format(page))
        items = re.findall(r'<div data-episode-slug="([^"]*)" class="playlist-block-item w-dyn-item"(.*?)(?=<div data-episode-slug=|<div class="w-pagination-wrapper|$)', h, re.S)
        if not items:
            break
        for slug, body in items:
            attr = lambda n: (lambda m: html.unescape(m.group(1)) if m else None)(re.search(rf'data-{n}="([^"]*)"', body))
            epnum = re.search(r'<div>\s*(?:\xa0|&nbsp;| )E\s*</div>\s*<div>\s*(\d+)\s*</div>', body)
            img = re.search(r'imagedelivery\.net/([^"]*)/sm"', body)
            desc = re.search(r'episode-item-desc w-richtext"><p>(.*?)</p>', body, re.S)
            dark = re.search(r'ep-theme-dark" style="display:none;">(#[0-9a-fA-F]+)', body)
            acc = re.search(r'ep-theme-accent-500" style="display:none;">(#[0-9a-fA-F]+)', body)
            eps.append(dict(slug=slug, title=attr("episode-title"), date=attr("episode-date"), season=attr("episode-season"),
                            episode=int(epnum.group(1)) if epnum else None, duration=int(attr("duration") or 0),
                            image=f"https://imagedelivery.net/{img.group(1)}/sm" if img else None,
                            desc=html.unescape(re.sub("<[^>]+>", "", desc.group(1)))[:300] if desc else None,
                            dark=dark.group(1) if dark else None, accent=acc.group(1) if acc else None))
        print(f"page {page}: {len(items)} episodes")
        page += 1
    return eps

def svg_uri(s):
    s = re.sub(r"<\?xml[^>]*\?>", "", s); s = re.sub(r"\s+", " ", s).strip()
    for a, b in (("#", "%23"), ('"', "%27"), ("'", "%27"), ("<", "%3C"), (">", "%3E")):
        s = s.replace(a, b)
    return "data:image/svg+xml;utf8," + s

def cover(e):
    e["cover"] = None
    if not e["image"]:
        return
    try:
        b = fetch(e["image"], binary=True)
    except Exception as ex:
        print("cover failed", e["slug"], ex); return
    if b.lstrip().startswith(b"<"):
        s = b.decode()
        if len(s) <= MAX_SVG:
            e["cover"] = svg_uri(s)
        return
    # raster: shrink with macOS sips (falls back to the original bytes elsewhere)
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "in"), os.path.join(d, "out.jpg")
        open(src, "wb").write(b)
        r = subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "62", "-Z", "220", src, "--out", dst], capture_output=True)
        data = open(dst, "rb").read() if r.returncode == 0 and os.path.exists(dst) else b
        mime = "image/jpeg" if r.returncode == 0 else ("image/png" if b[:4] == b"\x89PNG" else "image/jpeg")
        e["cover"] = f"data:{mime};base64," + base64.b64encode(data).decode()

if __name__ == "__main__":
    eps = scrape_list()
    with ThreadPoolExecutor(6) as ex:
        list(ex.map(cover, eps))
    out = [{k: e.get(k) for k in ["slug", "title", "date", "season", "episode", "duration", "dark", "accent", "desc", "cover"]} for e in eps]
    js = "window.EPISODES=" + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";"
    open(OUT, "w").write(js)
    print(f"wrote {OUT}: {len(out)} episodes, {sum(1 for e in out if e['cover'])} covers, {len(js)/1e6:.1f} MB")
