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
    "morluto/rea": ("REA", "morluto", "Mach-O analysis, provider diagnostics, V8 cached data", [9570, 9603, 9501]),
    "QwenLM/qwen-code": ("Qwen Code", "QwenLM", "Loop controls, shell detection, release CI", [17048, 16491, 15852]),
    "Tencent/AI-Infra-Guard": ("AI-Infra-Guard", "Tencent", "NVD advisories for AI products", [745]),
    "agentscope-ai/OpenJudge": ("OpenJudge", "agentscope-ai", "JSON validation, grader configuration", [226, 218, 222]),
    "bytedance/deer-flow": ("DeerFlow", "ByteDance", "Message parsing, agent memory, subagent state", [8066, 8146, 8167]),
    "agentscope-ai/agentscope": ("agentscope", "agentscope-ai", "Knowledge retrieval, upload parsing, Gemini TTS", [3976, 3986, 4038]),
    "Yuan1z0825/nature-skills": ("Nature Skills", "Yuan1z0825", "Editable text in PDF figures", [284]),
}


def render(pages, owner):
    projects = defaultdict(dict)
    excluded = {f"{owner}/{owner}".lower(), "2sincejuly/skydot"}
    for page in pages:
        for pr in page["data"]["user"]["pullRequests"]["nodes"]:
            repo = pr["repository"]["nameWithOwner"]
            if not pr["repository"]["isPrivate"] and repo.lower() not in excluded:
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
        rows.append(
            f'<tr><td><strong><a href="{url}">{escape(display)}</a></strong> '
            f'<a href="{url}/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/{repo}'
            f'?style=flat-square&amp;label=%E2%98%85&amp;labelColor=163656&amp;color=426E92"></a></td>'
            f'<td>{escape(org)}</td><td><a href="{url}/pulls?{search}"><img alt="{count} merged PRs" '
            f'src="https://img.shields.io/badge/PRs-{count}-24547B?style=flat-square&amp;labelColor=163656">'
            f'</a></td><td>{escape(focus)}</td></tr>'
        )
        highlights.append(f"<p><strong>{escape(org)} · {escape(display)}</strong></p>\n<ul>")
        for number in ([n for n in pinned if n in prs] or sorted(prs, reverse=True)[:3]):
            title = re.sub(r"^[a-z]+(?:\([^)]*\))?!?: ", "", prs[number])
            label = escape(title[:1].upper() + title[1:])
            highlights.append(f'<li><a href="{url}/pull/{number}">{label}</a></li>')
        highlights.append("</ul>")
    return "\n".join([
        "<table>", "<thead><tr><th>Project</th><th>Org</th><th>Merged</th><th>Focus</th></tr></thead>",
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
