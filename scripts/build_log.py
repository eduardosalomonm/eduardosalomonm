"""Rewrite the Build log section of README.md from public repository activity.

Only public, non-archived, non-fork repositories are read, so private work
never appears in the profile. Run by .github/workflows/build-log.yml.
"""
import datetime
import json
import os
import re
import urllib.request

USER = "eduardosalomonm"
README = "README.md"
ROWS = 5
START, END = "<!-- build-log:start -->", "<!-- build-log:end -->"


def api(path):
    request = urllib.request.Request(f"https://api.github.com/{path}")
    request.add_header("Accept", "application/vnd.github+json")
    if os.environ.get("GITHUB_TOKEN"):
        request.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def when(iso, today):
    days = (today - datetime.date.fromisoformat(iso[:10])).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days} days ago"
    weeks = days // 7
    return f"{weeks} week{'s' if weeks > 1 else ''} ago"


def housekeeping(path):
    name = path.rsplit("/", 1)[-1].upper()
    return name.endswith(".MD") or name.startswith("LICENSE")


def latest_code_commit(repo):
    """Newest commit that changes more than docs or the licence."""
    for item in api(f"repos/{USER}/{repo}/commits?per_page=15"):
        files = api(f"repos/{USER}/{repo}/commits/{item['sha']}").get("files", [])
        if files and not all(housekeeping(f["filename"]) for f in files):
            return item["commit"]
    return None


def build_table(today):
    repos = [
        repo for repo in api(f"users/{USER}/repos?type=owner&per_page=100")
        if not repo["fork"] and not repo["archived"] and repo["name"] != USER
    ]
    rows = []
    for repo in repos:
        commit = latest_code_commit(repo["name"])
        if commit:
            rows.append((commit["committer"]["date"], repo, commit["message"].splitlines()[0]))
    rows.sort(key=lambda row: row[0], reverse=True)

    lines = ["| When | Project | Latest commit |", "| --- | --- | --- |"]
    for date, repo, message in rows[:ROWS]:
        message = message.replace("|", "\\|")
        if len(message) > 72:
            message = message[:71].rstrip() + "…"
        lines.append(f"| {when(date, today)} | [{repo['name']}]({repo['html_url']}) | {message} |")
    return "\n".join(lines)


def main():
    with open(README, encoding="utf-8") as handle:
        text = handle.read()
    table = build_table(datetime.date.today())
    pattern = re.compile(re.escape(START) + ".*?" + re.escape(END), re.S)
    updated = pattern.sub(f"{START}\n{table}\n{END}", text)
    with open(README, "w", encoding="utf-8") as handle:
        handle.write(updated)


if __name__ == "__main__":
    main()
