"""
Quest Log CRT: runs on GitHub Actions every 6 hours.

1. Asks the GitHub API for your public repositories.
2. Keeps the ones created THIS year (no forks, no profile README repo).
3. Draws two images using the pixel background and the Unifont font:
     assets/quest-log.png     -> project list + a "LOADING..." slot
     assets/player-stats.png  -> simple stats bar
To test offline:  DEMO=1 python scripts/quest_log.py
"""
import datetime as dt
import glob
import json
import os
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
USER = os.environ.get("GH_USER", "sebasGDevelop")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
YEAR = dt.datetime.now(dt.timezone.utc).year
MAX_ROWS = 4  # how many projects fit on screen (the most recent ones are shown)

CREAM, CYAN, RED, AMBER, DIM = (242, 240, 230), (51, 214, 255), (255, 51, 85), (255, 196, 92), (176, 170, 200)


# ---------------------------------------------------------------- data
def api(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "quest-log")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def get_data():
    if os.environ.get("DEMO"):
        repos = [
            {"name": "medieval-market", "description": "Medieval-themed e-commerce store", "language": "C#"},
            {"name": "growth-app", "description": "Personal growth and organization app", "language": "Python"},
        ]
        return repos, {"repos": 2, "contrib": 37, "stars": 1, "followers": 3}

    all_repos = api(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner&sort=created&direction=asc")
    mine = [r for r in all_repos if not r["fork"] and r["name"].lower() != USER.lower()]
    this_year = [r for r in mine if r["created_at"].startswith(str(YEAR))]

    contrib = None
    try:
        q = """query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){
                 contributionsCollection(from:$f,to:$t){contributionCalendar{totalContributions}}
                 followers{totalCount}}}"""
        res = api("https://api.github.com/graphql", {"query": q, "variables": {
            "u": USER, "f": f"{YEAR}-01-01T00:00:00Z", "t": f"{YEAR}-12-31T23:59:59Z"}})
        u = res["data"]["user"]
        contrib = u["contributionsCollection"]["contributionCalendar"]["totalContributions"]
        followers = u["followers"]["totalCount"]
    except Exception as e:  # if GraphQL fails, fall back to the basics
        print("GraphQL unavailable:", e)
        followers = api(f"https://api.github.com/users/{USER}")["followers"]

    stats = {
        "repos": len(this_year),
        "contrib": contrib if contrib is not None else "-",
        "stars": sum(r["stargazers_count"] for r in mine),
        "followers": followers,
    }
    return this_year, stats


# ---------------------------------------------------------------- drawing
def font(size):
    for p in ["/usr/share/fonts/opentype/unifont/unifont.otf", "/usr/share/fonts/truetype/unifont/unifont.ttf",
              *glob.glob("/usr/share/fonts/**/unifont.*tf", recursive=True)]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    raise SystemExit("Unifont font not found (install fonts-unifont)")


F = font(32)


def fit(d, text, max_w):
    """Trims the text with '…' if it does not fit."""
    if d.textlength(text, font=F) <= max_w:
        return text
    while text and d.textlength(text + "…", font=F) > max_w:
        text = text[:-1]
    return text.rstrip() + "…"


def crt(img, k=0.085, radius=70, pad=26):
    """Scanlines, chromatic aberration, curved screen, vignette and bezel."""
    a = np.asarray(img).astype(np.float32) / 255
    h, w, _ = a.shape
    a[:, 2:, 0] = a[:, :-2, 0]
    a[:, :-2, 2] = a[:, 2:, 2]
    scan = np.ones((h, 1, 1), np.float32)
    scan[2::3] = 0.72
    a = np.clip(a * scan * 1.08, 0, 1)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = xx / w * 2 - 1, yy / h * 2 - 1
    r2 = nx * nx + ny * ny
    mx = (((nx * (1 + k * r2)) + 1) / 2 * (w - 1)).round().astype(int)
    my = (((ny * (1 + k * r2)) + 1) / 2 * (h - 1)).round().astype(int)
    ok = (mx >= 0) & (mx < w) & (my >= 0) & (my < h)
    out = np.zeros_like(a)
    out[ok] = a[my[ok], mx[ok]]
    out *= (1 - np.clip(np.abs(nx) ** 6 + np.abs(ny) ** 6, 0, 1) * 0.55 - r2 * 0.12)[..., None]
    screen = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))

    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    frame = Image.new("RGB", (w + pad * 2, h + pad * 2), (14, 14, 18))
    fd = ImageDraw.Draw(frame)
    fd.rounded_rectangle((0, 0, frame.width - 1, frame.height - 1), radius=radius - 10, fill=(22, 22, 26))
    fd.rounded_rectangle((pad - 8, pad - 8, pad + w + 7, pad + h + 7), radius=radius + 8, fill=(6, 6, 8))
    frame.paste(screen, (pad, pad), mask)

    glare = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glare)
    for i in range(40):
        if pad + h * 0.35 - i <= pad + 12 + i:
            break
        gd.ellipse((pad + 40 + i, pad + 12 + i, pad + w * 0.6 - i, pad + h * 0.35 - i), fill=(255, 255, 255, 1))
    return Image.alpha_composite(frame.convert("RGBA"), glare)


def panel(img, box, title):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle(box, fill=(10, 10, 22, 165))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(img)
    d.fontmode = "1"
    x0, y0, x1, y1 = box
    d.rectangle(box, outline=CREAM, width=4)
    tw = d.textlength(title, font=F)
    d.rectangle((x0 + 24, y0 - 18, x0 + 24 + tw, y0 + 18), fill=(26, 20, 56))
    d.text((x0 + 24, y0 - 18), title, font=F, fill=CREAM)
    return img, d


def quest_log(bg, repos):
    img = bg.resize((bg.width * 3, bg.height * 3), Image.NEAREST)
    box = (78, 74, 786, 500)
    img, d = panel(img, box, f" Sebas' Quest Log {YEAR} ")
    L, R = box[0] + 32, box[2] - 32

    shown = repos[-MAX_ROWS:]
    first = len(repos) - len(shown) + 1
    y = box[1] + 38
    for i, r in enumerate(shown):
        lang = r.get("language") or ""
        lw = d.textlength(lang, font=F)
        d.text((L, y), f"{first + i:02d}", font=F, fill=CYAN)
        d.text((L + 64, y), fit(d, r["name"], R - L - 64 - lw - 24), font=F, fill=CREAM)
        d.text((R - lw, y), lang, font=F, fill=AMBER)
        desc = r.get("description") or "no description"
        d.text((L + 64, y + 34), fit(d, desc, R - L - 64), font=F, fill=DIM)
        y += 80

    # the slot for the next project
    d.text((L, y), f"{len(repos) + 1:02d}", font=F, fill=CYAN)
    d.text((L + 64, y), "LOADING...", font=F, fill=RED)
    if len(repos) > MAX_ROWS:
        more = f"+{len(repos) - MAX_ROWS} more"
        d.text((R - d.textlength(more, font=F), y), more, font=F, fill=DIM)
    return crt(img)


def player_stats(bg, s):
    sky = bg.crop((0, 0, bg.width, 54))
    sky.paste(bg.crop((100, 8, 140, 54)), (210, 8))  # cover the moon and flags with sky
    sky.paste(bg.crop((100, 40, 170, 54)), (176, 40))
    strip = sky.resize((bg.width * 3, 54 * 3), Image.NEAREST)
    box = (56, 34, strip.width - 56, strip.height - 16)
    img, d = panel(strip, box, " player_stats ")
    cells = [("REPOS", s["repos"]), ("CONTRIB.", s["contrib"]), ("STARS", s["stars"]), ("FOLLOWERS", s["followers"])]
    cw = (box[2] - box[0]) / len(cells)
    for i, (label, val) in enumerate(cells):
        cx = box[0] + cw * i + cw / 2
        for text, yy, col in ((label, box[1] + 18, DIM), (str(val), box[1] + 52, AMBER)):
            d.text((cx - d.textlength(text, font=F) / 2, yy), text, font=F, fill=col)
    return crt(img, k=0.03, radius=40, pad=18)


def main():
    repos, stats = get_data()
    bg = Image.open(os.path.join(ASSETS, "quest-bg.png")).convert("RGB")
    quest_log(bg, repos).save(os.path.join(ASSETS, "quest-log.png"), optimize=True)
    player_stats(bg, stats).save(os.path.join(ASSETS, "player-stats.png"), optimize=True)
    print(f"{len(repos)} repos in {YEAR}:", [r["name"] for r in repos], stats)


if __name__ == "__main__":
    main()
