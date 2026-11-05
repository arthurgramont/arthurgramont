#!/usr/bin/env python3
"""Génère la carte « Recent activity » (SVG) à partir des événements publics GitHub.

Seuls le type d'événement, le repo et la date sont utilisés (pas de messages de
commit). Les pushs d'un même jour sur un même repo sont regroupés.

Variables d'environnement :
  GITHUB_TOKEN   fourni automatiquement par GitHub Actions
  GH_USER        ton nom d'utilisateur GitHub
  OUT            chemin du SVG de sortie (défaut : activity.svg)
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape

COLORS = {"push": "#7dd3fc", "pr": "#c4b5fd", "issue": "#f0abfc", "create": "#86efac", "fork": "#fde68a"}


def fetch(token, user):
    req = urllib.request.Request(
        f"https://api.github.com/users/{user}/events/public?per_page=100",
        headers={"Authorization": f"Bearer {token}", "User-Agent": "profile-activity"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def describe(ev):
    """(clé couleur, texte) ou None si l'événement n'est pas retenu."""
    repo = ev["repo"]["name"].split("/")[-1]
    p = ev.get("payload", {})
    t = ev["type"]
    if t == "PushEvent":
        return "push", f"Pushed to {repo}"
    if t == "PullRequestEvent":
        action = "Merged" if p.get("pull_request", {}).get("merged") else p.get("action", "updated").capitalize()
        return "pr", f"{action} a pull request in {repo}"
    if t == "IssuesEvent":
        return "issue", f"{p.get('action', 'updated').capitalize()} an issue in {repo}"
    if t == "CreateEvent" and p.get("ref_type") == "repository":
        return "create", f"Created {repo}"
    if t == "ForkEvent":
        return "fork", f"Forked a repository into {repo}"
    return None


def collapse(events, n=5):
    seen, out = set(), []
    for ev in events:
        d = describe(ev)
        if not d:
            continue
        key = (d, ev["created_at"][:10])
        if key in seen:
            continue
        seen.add(key)
        out.append((d[0], d[1], ev["created_at"]))
        if len(out) == n:
            break
    return out


def ago(iso, now=None):
    now = now or datetime.now(timezone.utc)
    delta = now - datetime.fromisoformat(iso.replace("Z", "+00:00"))
    h = int(delta.total_seconds() // 3600)
    if h < 1:
        return "just now"
    if h < 24:
        return f"{h}h ago"
    d = delta.days
    return f"{d}d ago" if d < 14 else f"{d // 7}w ago"


def render(items, now=None):
    rows = ""
    for i, (kind, text, when) in enumerate(items):
        y = 70 + i * 31
        rows += (
            f'<circle cx="36" cy="{y - 5}" r="5" fill="{COLORS[kind]}"/>'
            f'<text class="t" x="54" y="{y}">{escape(text)}</text>'
            f'<text class="a" x="790" y="{y}" text-anchor="end">{ago(when, now)}</text>'
        )
        if i < len(items) - 1:
            rows += f'<line x1="30" y1="{y + 13}" x2="790" y2="{y + 13}" stroke="#2c2c3e"/>'
    if not items:
        rows = '<text class="a" x="30" y="90">No recent public activity.</text>'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="820" height="220" viewBox="0 0 820 220" role="img"
     aria-label="Recent public GitHub activity">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#1b1b2e"/><stop offset="1" stop-color="#121221"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }}
    .h {{ font-size: 10.5px; font-weight: 700; letter-spacing: 1.6px; fill: #9a9aa6; }}
    .t {{ font-size: 14px; fill: #e4e4ea; }}
    .a {{ font-size: 12px; fill: #8f8fa0; }}
  </style>
  <rect width="820" height="220" rx="16" fill="url(#bg)" stroke="#2c2c3e"/>
  <text class="h" x="30" y="32">RECENT ACTIVITY</text>
  {rows}
</svg>
"""


def main():
    token, user = os.environ.get("GITHUB_TOKEN"), os.environ.get("GH_USER")
    if not token or not user:
        sys.exit("GITHUB_TOKEN et GH_USER sont requis")
    out = os.environ.get("OUT", "activity.svg")
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(collapse(fetch(token, user))))
    print(f"écrit : {out}")


if __name__ == "__main__":
    main()
