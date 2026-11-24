"""Refresh the profile contribution table from paginated GitHub PR data."""

import json
import re
import sys
from collections import defaultdict
from html import escape
from pathlib import Path
from urllib.parse import urlencode

# Display names, focus areas, and representative PRs shown on the profile.
PROJECTS = {
    "morluto/rea": ("REA", "morluto", "Mach-O/IPS analysis, process sandbox, SQLite paging", [9570, 8469, 9331, 9108]),
    "QwenLM/qwen-code": ("Qwen Code", "QwenLM", "MCP tool routing, telemetry, shell context", [15757, 16495, 16491]),
    "Tencent/AI-Infra-Guard": ("AI-Infra-Guard", "Tencent", "NVD advisories for AI products", [742]),
    "agentscope-ai/OpenJudge": ("OpenJudge", "agentscope-ai", "Evaluation prompts, grader validation", [224, 226, 218]),
    "bytedance/deer-flow": ("DeerFlow", "ByteDance", "Thread lifecycle, agent memory, message parsing", [8036, 8146, 8066]),
    "agentscope-ai/agentscope": ("agentscope", "agentscope-ai", "RAG upload routing, multi-tenant context", [3986, 3976]),
    "Yuan1z0825/nature-skills": ("Nature Skills", "Yuan1z0825", "Editable text in PDF figures", [284]),
    "pingdotgg/t3code": ("T3 Code", "pingdotgg", "Work-log image layout", [41597]),
    "stablyai/orca": ("Orca", "stablyai", "Droid hooks, Claude plan labels, usage reporting", [47853, 47836, 47804]),
}


def write_star_badge(repo, count):
    value = f"{count / 1000:.1f}K" if count >= 1000 else str(count)
    number_width = 10 + 7 * len(value)
    width = 59 + number_width
    path = Path("assets/stars") / f"{repo}.svg"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="{count:,} stars">
  <title>{count:,} stars</title>
  <defs>
    <linearGradient id="face" x2="0" y2="1" gradientUnits="objectBoundingBox">
      <stop stop-color="#fff"/><stop offset="1" stop-color="#f2f3f4"/>
    </linearGradient>
  </defs>
  <rect x=".5" y=".5" width="54" height="19" rx="3" fill="url(#face)" stroke="#d0d3d6"/>
  <rect x="59.5" y=".5" width="{number_width - 1}" height="19" rx="3" fill="#fafafa" stroke="#d0d3d6"/>
  <path fill="#fb6571" transform="translate(4 4)" d="M1 1h4v1h2V1h4v1h1v5h-1v1h-1v1H9v1H8v1H7v1H5v-1H4v-1H3V9H2V8H1V7H0V2h1z"/>
  <g font-family="Arial, sans-serif" font-size="11" font-weight="bold" fill="#333">
    <text x="21" y="14">Stars</text>
    <text x="{59 + number_width / 2:g}" y="14" text-anchor="middle">{value}</text>
  </g>
</svg>
''')
    return path.as_posix()


def render(pages, owner):
    projects = defaultdict(dict)
    stars = {}
    profile_owner = owner.casefold()
    for page in pages:
        for pr in page["data"]["user"]["pullRequests"]["nodes"]:
            repo = pr["repository"]["nameWithOwner"]
            if not pr["repository"]["isPrivate"] and repo.split("/", 1)[0].casefold() != profile_owner:
                stars[repo] = pr["repository"]["stargazerCount"]
                projects[repo][pr["number"]] = pr["title"]
    if not projects:
        raise ValueError("No public contributions returned")

    rows, highlights = [], []
    order = {repo: index for index, repo in enumerate(PROJECTS)}
    for repo in sorted(projects, key=lambda r: (-len(projects[r]), order.get(r, len(order)), r)):
        prs = projects[repo]
        org, name = repo.split("/")
        display, org, focus, pinned = PROJECTS.get(repo, (name, org, prs[max(prs)], []))
        url = f"https://github.com/{repo}"
        count = len(prs)
        search = urlencode({"q": f"is:pr is:merged author:{owner}"})
        star_badge = write_star_badge(repo, stars[repo])
        rows.append(
            f'<tr><td><strong><a href="{url}">{escape(display)}</a></strong></td><td>'
            f'<a href="{url}/stargazers"><img src="{star_badge}" alt="{stars[repo]:,} stars"></a></td>'
            f'<td>{escape(org)}</td><td><a href="{url}/pulls?{search}"><img alt="{count} merged PRs" '
            f'src="https://img.shields.io/badge/PRs-{count}-white?style=social&amp;logo=git&amp;logoColor=669477">'
            f'</a></td><td>{escape(focus)}</td></tr>'
        )
        highlights.append(f"<p><strong>{escape(org)} · {escape(display)}</strong></p>\n<ul>")
        for number in ([n for n in pinned if n in prs] or sorted(prs, reverse=True)[:3]):
            title = re.sub(r"^[a-z]+(?:\([^)]*\))?!?: ", "", prs[number])
            label = escape(title[:1].upper() + title[1:])
            highlights.append(f'<li><a href="{url}/pull/{number}">{label}</a></li>')
        highlights.append("</ul>")
    return "\n".join([
        "<table>", "<thead><tr><th>Project</th><th>Stars</th><th>Org</th><th>Merged</th><th>Focus</th></tr></thead>",
        "<tbody>", *rows, "</tbody>", "</table>", "", "<details>", "<summary><strong>Highlights</strong></summary>",
        "", *highlights, "</details>",
    ])


if __name__ == "__main__":
    readme = Path("README.md")
    before = readme.read_text()
    start, end = "<!-- CONTRIBUTIONS:START -->", "<!-- CONTRIBUTIONS:END -->"
    if before.count(start) != 1 or before.count(end) != 1 or before.index(start) >= before.index(end):
        raise ValueError("Invalid contribution markers")
    block = render(json.load(sys.stdin), sys.argv[1])
    readme.write_text(before.split(start)[0] + start + "\n" + block + "\n" + end + before.split(end)[1])
