#!/usr/bin/env python3
"""Génère une carte d'activité GitHub (SVG) : contributions, heatmap, langages.

Variables d'environnement :
  GITHUB_TOKEN   fourni automatiquement par GitHub Actions
  GH_USER        ton nom d'utilisateur GitHub
  OUT            chemin du SVG de sortie (défaut : stats.svg)

Aucune dépendance : bibliothèque standard uniquement.
"""
import json
import os
import sys
import urllib.request
from collections import defaultdict
from xml.sax.saxutils import escape

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, first: 100, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 8, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount } }
      }
    }
  }
}
"""

WEEKS = 33
LEVELS = ["#232640", "#3a4a8a", "#4f7fd1", "#7dd3fc", "#f0abfc"]


def fetch(token, login):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "profile-stats"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if "errors" in payload:
        sys.exit(json.dumps(payload["errors"]))
    return payload["data"]["user"]


def summarize(user):
    cc = user["contributionsCollection"]
    cal = cc["contributionCalendar"]
    weeks = [[d["contributionCount"] for d in w["contributionDays"]] for w in cal["weeks"]][-WEEKS:]

    langs, colors, stars = defaultdict(int), {}, 0
    for repo in user["repositories"]["nodes"]:
        stars += repo["stargazerCount"]
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]] += e["size"]
            colors[e["node"]["name"]] = e["node"]["color"] or "#8b8b99"
    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    return {
        "year": cal["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "prs": cc["totalPullRequestContributions"],
        "repos": user["repositories"]["totalCount"],
        "stars": stars,
        "weeks": weeks,
        "langs": [(n, s / total, colors[n]) for n, s in top],
    }


def level(count, peak):
    if count == 0 or peak == 0:
        return 0
    return min(4, 1 + int(3 * (count - 1) / max(peak, 1)))


def render(s):
    peak = max((c for w in s["weeks"] for c in w), default=0)
    cells = []
    for wi, week in enumerate(s["weeks"]):
        for di, c in enumerate(week):
            cells.append(
                f'<rect x="{290 + wi * 15}" y="{36 + di * 15}" width="12" height="12" rx="3" '
                f'fill="{LEVELS[level(c, peak)]}"/>'
            )

    stats = [(s["year"], "contributions this year"), (s["prs"], "pull requests"), (s["repos"], "public repos")]
    stat_svg = "".join(
        f'<text class="n" x="30" y="{64 + i * 40}">{n:,}</text>'
        f'<text class="l" x="30" y="{79 + i * 40}">{escape(label)}</text>'
        for i, (n, label) in enumerate(stats)
    )

    # barre des langages
    bar, legend, x, lx = [], [], 30, 30
    for name, share, color in s["langs"]:
        w = max(4, round(760 * share))
        bar.append(f'<rect x="{x}" y="172" width="{w}" height="8" fill="{color}"/>')
        x += w
        legend.append(
            f'<circle cx="{lx + 4}" cy="199" r="4" fill="{color}"/>'
            f'<text class="g" x="{lx + 14}" y="203">{escape(name)} {share * 100:.0f}%</text>'
        )
        lx += 30 + 7 * len(f"{name} {share * 100:.0f}%")

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="820" height="220" viewBox="0 0 820 220" role="img"
     aria-label="GitHub activity: {s['year']} contributions in the last year">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#1b1b2e"/><stop offset="1" stop-color="#121221"/>
    </linearGradient>
    <clipPath id="bar"><rect x="30" y="172" width="760" height="8" rx="4"/></clipPath>
  </defs>
  <style>
    text {{ font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }}
    .h {{ font-size: 10.5px; font-weight: 700; letter-spacing: 1.6px; fill: #9a9aa6; }}
    .n {{ font-size: 24px; font-weight: 800; fill: #f5f5f7; }}
    .l {{ font-size: 12px; fill: #8f8fa0; }}
    .g {{ font-size: 11.5px; fill: #c9c9d1; }}
  </style>
  <rect width="820" height="220" rx="16" fill="url(#bg)" stroke="#2c2c3e"/>
  <text class="h" x="30" y="32">GITHUB ACTIVITY</text>
  <text class="h" x="290" y="26" fill="#6b6b80">LAST {len(s['weeks'])} WEEKS</text>
  {stat_svg}
  {''.join(cells)}
  <g clip-path="url(#bar)"><rect x="30" y="172" width="760" height="8" fill="#232640"/>{''.join(bar)}</g>
  {''.join(legend)}
</svg>
"""


def main():
    token, login = os.environ.get("GITHUB_TOKEN"), os.environ.get("GH_USER")
    if not token or not login:
        sys.exit("GITHUB_TOKEN et GH_USER sont requis")
    out = os.environ.get("OUT", "stats.svg")
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(summarize(fetch(token, login))))
    print(f"écrit : {out}")


if __name__ == "__main__":
    main()
