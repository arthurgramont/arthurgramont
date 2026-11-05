#!/usr/bin/env python3
"""Génère la carte « Latest work » (SVG) : tes 4 repos publics les plus récemment actifs.

Variables d'environnement :
  GITHUB_TOKEN   fourni automatiquement par GitHub Actions
  GH_USER        ton nom d'utilisateur GitHub
  OUT            chemin du SVG de sortie (défaut : repos.svg)
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape

LANG_COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "PHP": "#4F5D95",
    "HCL": "#844FBA", "Shell": "#89e051", "Dockerfile": "#384d54", "HTML": "#e34c26",
    "CSS": "#663399", "Vue": "#41b883", "Jupyter Notebook": "#DA5B0B", "Twig": "#c1d026",
    "Dart": "#00B4AB", "Kotlin": "#A97BFF", "Swift": "#F05138", "Go": "#00ADD8",
}


def fetch(token, user):
    req = urllib.request.Request(
        f"https://api.github.com/users/{user}/repos?sort=pushed&per_page=30&type=owner",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "profile-repos"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def pick(repos, user, n=4):
    out = [
        r for r in repos
        if not r["fork"] and not r["archived"] and r["name"].lower() != user.lower()
    ]
    return out[:n]


def ago(iso, now=None):
    now = now or datetime.now(timezone.utc)
    d = (now - datetime.fromisoformat(iso.replace("Z", "+00:00"))).days
    if d <= 0:
        return "today"
    if d < 7:
        return f"{d}d ago"
    if d < 60:
        return f"{d // 7}w ago"
    return f"{d // 30}mo ago"


def clip(t, n):
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def render(repos, now=None):
    cards = ""
    for i, r in enumerate(repos):
        x, y = 30 + (i % 2) * 385, 46 + (i // 2) * 86
        lang = r.get("language")
        color = LANG_COLORS.get(lang, "#8b8b99")
        desc = r.get("description") or "No description yet"
        meta = ""
        mx = x + 18
        if lang:
            meta += f'<circle cx="{mx + 4}" cy="{y + 62}" r="4" fill="{color}"/><text class="m" x="{mx + 14}" y="{y + 66}">{escape(lang)}</text>'
            mx += 24 + 7 * len(lang)
        if r["stargazers_count"]:
            meta += f'<text class="m" x="{mx}" y="{y + 66}">★ {r["stargazers_count"]}</text>'
        cards += (
            f'<rect x="{x}" y="{y}" width="370" height="76" rx="12" fill="#1f2035" stroke="#2c2c3e"/>'
            f'<text class="n" x="{x + 18}" y="{y + 26}">{escape(clip(r["name"], 36))}</text>'
            f'<text class="d" x="{x + 18}" y="{y + 46}">{escape(clip(desc, 56))}</text>'
            f'{meta}'
            f'<text class="m" x="{x + 352}" y="{y + 66}" text-anchor="end">{ago(r["pushed_at"], now)}</text>'
        )
    if not repos:
        cards = '<text class="d" x="30" y="90">Nothing public yet. Stay tuned.</text>'

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="820" height="220" viewBox="0 0 820 220" role="img"
     aria-label="Latest work: most recently active public repositories">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#1b1b2e"/><stop offset="1" stop-color="#121221"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }}
    .h {{ font-size: 10.5px; font-weight: 700; letter-spacing: 1.6px; fill: #9a9aa6; }}
    .n {{ font-size: 15px; font-weight: 700; fill: #7dd3fc; }}
    .d {{ font-size: 12.5px; fill: #b4b4c2; }}
    .m {{ font-size: 11.5px; fill: #8f8fa0; }}
  </style>
  <rect width="820" height="220" rx="16" fill="url(#bg)" stroke="#2c2c3e"/>
  <text class="h" x="30" y="30">LATEST WORK</text>
  {cards}
</svg>
"""


def main():
    token, user = os.environ.get("GITHUB_TOKEN"), os.environ.get("GH_USER")
    if not token or not user:
        sys.exit("GITHUB_TOKEN et GH_USER sont requis")
    out = os.environ.get("OUT", "repos.svg")
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(pick(fetch(token, user), user)))
    print(f"écrit : {out}")


if __name__ == "__main__":
    main()
