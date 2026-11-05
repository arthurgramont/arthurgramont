#!/usr/bin/env python3
"""Génère la carte « Featured project » (SVG) pour un repo public (ex. Seego).

Variables d'environnement :
  GITHUB_TOKEN     fourni automatiquement par GitHub Actions
  GH_USER          ton nom d'utilisateur GitHub
  PROJECT_REPO     "owner/repo" du projet (si vide : détecté dans tes événements
                   publics récents à partir de PROJECT_NAME)
  PROJECT_NAME     nom du repo à chercher si PROJECT_REPO est vide (défaut : seego)
  PROJECT_TAGLINE  phrase affichée si le repo n'a pas de description
  PROJECT_URL      lien affiché en bas (défaut : homepage du repo)
  OUT              chemin du SVG de sortie (défaut : project.svg)
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape

IGNORED_LANGS = {"Jupyter Notebook", "Dockerfile", "Makefile"}
COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "PHP": "#4F5D95",
    "HCL": "#844FBA", "Shell": "#89e051", "HTML": "#e34c26", "CSS": "#663399", "Vue": "#41b883",
    "Twig": "#c1d026", "Dart": "#00B4AB", "SCSS": "#c6538c", "Go": "#00ADD8", "Java": "#b07219",
}


def api(token, path, default=None):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "profile-project"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except (urllib.error.URLError, TimeoutError):
        return default


def find_repo(token, user, name):
    events = api(token, f"/users/{user}/events/public?per_page=100", []) or []
    for ev in events:
        full = ev["repo"]["name"]
        if full.split("/")[-1].lower() == name.lower():
            return full
    return None


def collect(token, repo):
    info = api(token, f"/repos/{repo}")
    if not info:
        return None
    since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    commits = api(token, f"/repos/{repo}/commits?since={since}T00:00:00Z&per_page=100", None)
    q = urllib.parse.quote(f"repo:{repo} is:pr is:merged merged:>={since}")
    merged = api(token, f"/search/issues?q={q}&per_page=1", None)
    contributors = api(token, f"/repos/{repo}/contributors?per_page=100", None)
    langs = api(token, f"/repos/{repo}/languages", {}) or {}
    return {
        "name": info["name"],
        "description": info.get("description"),
        "homepage": info.get("homepage"),
        "pushed_at": info["pushed_at"],
        "commits": None if commits is None else len(commits),
        "merged": None if merged is None else merged.get("total_count"),
        "contributors": None if contributors is None else len(contributors),
        "langs": {k: v for k, v in langs.items() if k not in IGNORED_LANGS},
    }


def ago(iso, now=None):
    now = now or datetime.now(timezone.utc)
    d = (now - datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    return "today" if d <= 0 else f"{d}d ago" if d < 14 else f"{d // 7}w ago" if d < 60 else f"{d // 30}mo ago"


def clip(t, n):
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def fmt(v, cap=100):
    if v is None:
        return "—"
    return f"{cap}+" if v >= cap else str(v)


def render(d, tagline="", url="", now=None):
    desc = d.get("description") or tagline or ""
    total = sum(d["langs"].values()) or 1
    top = sorted(d["langs"].items(), key=lambda kv: -kv[1])[:4]
    bar, legend, x, lx = "", "", 30, 30
    for name, size in top:
        w = max(4, round(760 * size / total))
        color = COLORS.get(name, "#8b8b99")
        bar += f'<rect x="{x}" y="156" width="{w}" height="8" fill="{color}"/>'
        x += w
        label = f"{name} {size / total * 100:.0f}%"
        legend += f'<circle cx="{lx + 4}" cy="183" r="4" fill="{color}"/><text class="m" x="{lx + 14}" y="187">{escape(label)}</text>'
        lx += 30 + 7 * len(label)

    stats = [(fmt(d["commits"]), "commits · 30d"), (fmt(d["merged"], 1000), "PRs merged · 30d"), (fmt(d["contributors"]), "contributors")]
    stat_svg = "".join(
        f'<text class="n" x="{440 + i * 120}" y="76">{escape(v)}</text><text class="m" x="{440 + i * 120}" y="94">{escape(lbl)}</text>'
        for i, (v, lbl) in enumerate(stats)
    )
    link = url or d.get("homepage") or ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="820" height="220" viewBox="0 0 820 220" role="img"
     aria-label="Featured project: {escape(d['name'])}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#1b1b2e"/><stop offset="1" stop-color="#121221"/>
    </linearGradient>
    <linearGradient id="nm" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#7dd3fc"/><stop offset="1" stop-color="#f0abfc"/>
    </linearGradient>
    <clipPath id="bar"><rect x="30" y="156" width="760" height="8" rx="4"/></clipPath>
  </defs>
  <style>
    text {{ font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }}
    .h {{ font-size: 10.5px; font-weight: 700; letter-spacing: 1.6px; fill: #9a9aa6; }}
    .name {{ font-size: 34px; font-weight: 800; fill: url(#nm); }}
    .d {{ font-size: 13.5px; fill: #c9c9d1; }}
    .n {{ font-size: 26px; font-weight: 800; fill: #f5f5f7; }}
    .m {{ font-size: 11.5px; fill: #8f8fa0; }}
  </style>
  <rect width="820" height="220" rx="16" fill="url(#bg)" stroke="#2c2c3e"/>
  <text class="h" x="30" y="32">FEATURED PROJECT</text>
  <text class="name" x="30" y="78">{escape(d['name'].capitalize())}</text>
  <text class="d" x="30" y="104">{escape(clip(desc, 52))}</text>
  <text class="m" x="30" y="126">Last push {ago(d['pushed_at'], now)}{' · ' + escape(link.replace('https://', '').rstrip('/')) if link else ''}</text>
  {stat_svg}
  <g clip-path="url(#bar)"><rect x="30" y="156" width="760" height="8" fill="#232640"/>{bar}</g>
  {legend}
</svg>
"""


def placeholder(name):
    return render({"name": name, "description": "Details coming soon", "pushed_at": datetime.now(timezone.utc).isoformat(),
                   "commits": None, "merged": None, "contributors": None, "langs": {}})


def main():
    token, user = os.environ.get("GITHUB_TOKEN"), os.environ.get("GH_USER")
    if not token or not user:
        sys.exit("GITHUB_TOKEN et GH_USER sont requis")
    name = os.environ.get("PROJECT_NAME", "seego")
    repo = os.environ.get("PROJECT_REPO") or find_repo(token, user, name)
    data = collect(token, repo) if repo else None
    if repo is None:
        print(f"::warning::Repo '{name}' introuvable dans tes événements récents. Définis la variable PROJECT_REPO (owner/repo).")
    svg = render(data, os.environ.get("PROJECT_TAGLINE", ""), os.environ.get("PROJECT_URL", "")) if data else placeholder(name)
    with open(os.environ.get("OUT", "project.svg"), "w", encoding="utf-8") as f:
        f.write(svg)
    print("écrit :", repo or "placeholder")


if __name__ == "__main__":
    main()
