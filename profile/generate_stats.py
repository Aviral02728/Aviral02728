import json
import os
import urllib.parse
import urllib.request
from datetime import date, timedelta
from html import escape
from pathlib import Path

USERNAME = "Aviral02728"
API_URL = "https://api.github.com"
COLORS = {
    "C": "#555555",
    "C++": "#f34b7d",
    "CSS": "#563d7c",
    "HTML": "#e34c26",
    "Java": "#b07219",
    "JavaScript": "#f1e05a",
    "Jupyter Notebook": "#da5b0b",
    "Python": "#3572A5",
    "TypeScript": "#3178c6",
}


def auth_headers():
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_get(path):
    request = urllib.request.Request(
        f"{API_URL}/{path}",
        headers=auth_headers(),
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def github_graphql(query, variables):
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GH_TOKEN or GITHUB_TOKEN is required for contribution data")
    request = urllib.request.Request(
        f"{API_URL}/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            **auth_headers(),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        payload = json.load(response)
    if payload.get("errors"):
        messages = "; ".join(
            error.get("message", "Unknown GraphQL error")
            for error in payload["errors"]
        )
        raise RuntimeError(f"GitHub GraphQL request failed: {messages}")
    return payload["data"]


def repositories_for_user():
    repositories = []
    page = 1
    while True:
        batch = github_get(
            f"users/{USERNAME}/repos?"
            + urllib.parse.urlencode(
                {"type": "owner", "per_page": 100, "page": page}
            )
        )
        repositories.extend(repository for repository in batch if not repository["fork"])
        if len(batch) < 100:
            return repositories
        page += 1


def language_totals(repositories):
    totals = {}
    for repository in repositories:
        languages = github_get(
            f"repos/{USERNAME}/{repository['name']}/languages"
        )
        for language, byte_count in languages.items():
            totals[language] = totals.get(language, 0) + byte_count
    return totals


def current_streak():
    today = date.today()
    data = github_graphql(
        """
        query($login: String!, $from: DateTime!, $to: DateTime!) {
          user(login: $login) {
            contributionsCollection(from: $from, to: $to) {
              contributionCalendar {
                weeks {
                  contributionDays {
                    date
                    contributionCount
                  }
                }
              }
            }
          }
        }
        """,
        {
            "login": USERNAME,
            "from": f"{today - timedelta(days=366)}T00:00:00Z",
            "to": f"{today}T23:59:59Z",
        },
    )
    contributions = {
        day["date"]: day["contributionCount"]
        for week in data["user"]["contributionsCollection"]["contributionCalendar"][
            "weeks"
        ]
        for day in week["contributionDays"]
    }
    latest = today
    if contributions.get(latest.isoformat(), 0) == 0:
        latest -= timedelta(days=1)
    streak = 0
    while contributions.get(latest.isoformat(), 0) > 0:
        streak += 1
        latest -= timedelta(days=1)
    return streak


def stats_svg(user, stars, commits, pull_requests, issues, streak):
    contribution_total = commits + pull_requests + issues
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="980" height="560" viewBox="0 0 980 560"><title>{escape(USERNAME)}'s GitHub Stats</title><rect width="980" height="560" fill="#0d1117"/><g font-family="Arial,Helvetica,sans-serif"><rect x="1" y="1" width="978" height="245" rx="12" fill="#161b22" stroke="#30363d" stroke-width="2"/><text x="38" y="45" fill="#f0f6fc" font-size="29" font-weight="700">{escape(USERNAME)}'s GitHub Stats</text><g fill="#a8b0ba" font-size="19" font-weight="700"><text x="38" y="94">Total Stars Earned:</text><text x="435" y="94" fill="#f0f6fc">{stars}</text><text x="38" y="132">Total Commits:</text><text x="435" y="132" fill="#f0f6fc">{commits}</text><text x="38" y="170">Total PRs:</text><text x="435" y="170" fill="#f0f6fc">{pull_requests}</text><text x="38" y="208">Total Issues:</text><text x="435" y="208" fill="#f0f6fc">{issues}</text></g><circle cx="760" cy="135" r="77" fill="none" stroke="#3d444d" stroke-width="14"/><circle cx="760" cy="135" r="77" fill="none" stroke="#70a5fd" stroke-width="14" stroke-linecap="round" stroke-dasharray="34 450" transform="rotate(-90 760 135)"/><text x="760" y="148" text-anchor="middle" fill="#70a5fd" font-size="38" font-weight="700">{streak}</text><text x="760" y="190" text-anchor="middle" fill="#8b949e" font-size="14">day streak</text><rect x="1" y="274" width="978" height="285" rx="12" fill="#161b22" stroke="#30363d" stroke-width="2"/><line x1="327" y1="325" x2="327" y2="510" stroke="#c9d1d9" stroke-width="2"/><line x1="653" y1="325" x2="653" y2="510" stroke="#c9d1d9" stroke-width="2"/><text x="164" y="385" text-anchor="middle" fill="#f0f6fc" font-size="48" font-weight="700">{contribution_total}</text><text x="164" y="430" text-anchor="middle" fill="#f0f6fc" font-size="22">Total Contributions</text><text x="164" y="465" text-anchor="middle" fill="#8b949e" font-size="17">Public activity</text><circle cx="490" cy="375" r="48" fill="none" stroke="#ff9800" stroke-width="11"/><text x="490" y="388" text-anchor="middle" fill="#f0f6fc" font-size="34" font-weight="700">{streak}</text><text x="490" y="465" text-anchor="middle" fill="#ff9800" font-size="21" font-weight="700">Current Streak</text><text x="816" y="385" text-anchor="middle" fill="#f0f6fc" font-size="48" font-weight="700">{user["public_repos"]}</text><text x="816" y="430" text-anchor="middle" fill="#f0f6fc" font-size="22">Public Repositories</text><text x="816" y="465" text-anchor="middle" fill="#8b949e" font-size="17">{escape(USERNAME)}</text></g></svg>"""


def languages_svg(totals):
    total_bytes = sum(totals.values()) or 1
    top_languages = sorted(
        totals.items(), key=lambda item: item[1], reverse=True
    )[:6]
    segments = []
    rows = []
    offset = 38
    for index, (language, byte_count) in enumerate(top_languages):
        percentage = byte_count / total_bytes * 100
        width = max(8, round(percentage / 100 * 644))
        color = COLORS.get(language, "#8b949e")
        segments.append(
            f'<rect x="{offset}" y="78" width="{width}" height="18" '
            f'fill="{color}"/>'
        )
        offset += width
        x = 48 if index % 2 == 0 else 380
        y = 145 + (index // 2) * 50
        rows.append(
            f'<circle cx="{x}" cy="{y - 6}" r="10" fill="{color}"/>'
            f'<text x="{x + 22}" y="{y}" fill="#a8b0ba">'
            f"{escape(language)} {percentage:.2f}%</text>"
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="720" height="320" viewBox="0 0 720 320"><title>{escape(USERNAME)}'s Most Used Languages</title><rect width="720" height="320" rx="12" fill="#161b22" stroke="#30363d" stroke-width="2"/><g font-family="Arial,Helvetica,sans-serif"><text x="38" y="50" fill="#f0f6fc" font-size="29" font-weight="700">Most Used Languages</text>{''.join(segments)}{''.join(rows)}</g></svg>"""


def main():
    user = github_get(f"users/{USERNAME}")
    repositories = repositories_for_user()
    stars = sum(repository["stargazers_count"] for repository in repositories)
    commits = github_get(
        "search/commits?"
        + urllib.parse.urlencode({"q": f"author:{USERNAME}"})
    )["total_count"]
    pull_requests = github_get(
        "search/issues?"
        + urllib.parse.urlencode({"q": f"author:{USERNAME} type:pr"})
    )["total_count"]
    issues = github_get(
        "search/issues?"
        + urllib.parse.urlencode({"q": f"author:{USERNAME} type:issue"})
    )["total_count"]
    streak = current_streak()

    output_directory = Path("profile")
    output_directory.mkdir(exist_ok=True)
    output_directory.joinpath("stats.svg").write_text(
        stats_svg(user, stars, commits, pull_requests, issues, streak),
        encoding="utf-8",
    )
    output_directory.joinpath("top-langs.svg").write_text(
        languages_svg(language_totals(repositories)),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
