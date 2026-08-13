#!/usr/bin/env python3
"""Render a list of repos (mine or anyone else's) I've contributed to in the
past year -- commits, PRs, issues, or comments -- via GitHub's API.

Self-hosted on purpose: third-party badge services (e.g. the public
github-readme-stats Vercel instance) go down under load. This only depends
on GitHub's own API.
"""
import json
import os
import re
import subprocess

USERNAME = "byteshiftlabs"
README_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "README.md")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      commitContributionsByRepository(maxRepositories: 25) {
        repository { nameWithOwner url stargazerCount isPrivate }
      }
      pullRequestContributionsByRepository(maxRepositories: 25) {
        repository { nameWithOwner url stargazerCount isPrivate }
      }
      issueContributionsByRepository(maxRepositories: 25) {
        repository { nameWithOwner url stargazerCount isPrivate }
      }
    }
  }
}
"""


def gh_graphql(query, **fields):
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for k, v in fields.items():
        args += ["-f", f"{k}={v}"]
    result = subprocess.run(args, capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def gh_api(path):
    result = subprocess.run(
        ["gh", "api", path], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)


def collect_direct_contributions(repos):
    """Commits authored, PRs opened, issues opened -- these are 'real work' kinds."""
    data = gh_graphql(QUERY, login=USERNAME)
    collection = data["data"]["user"]["contributionsCollection"]

    for key in (
        "commitContributionsByRepository",
        "pullRequestContributionsByRepository",
        "issueContributionsByRepository",
    ):
        for entry in collection[key]:
            repo = entry["repository"]
            if repo["isPrivate"]:
                continue
            name = repo["nameWithOwner"]
            repos.setdefault(name, {
                "url": repo["url"],
                "stars": repo["stargazerCount"],
                "kinds": set(),
            })
            repos[name]["kinds"].add("work")


def collect_comment_contributions(repos):
    """Issues/PRs where I only left a comment, didn't open or author anything."""
    seen_repo_names = set()
    page = 1
    while page <= 5:
        result = gh_api(
            f"search/issues?q=commenter:{USERNAME}&per_page=100&page={page}"
        )
        items = result.get("items", [])
        if not items:
            break
        for item in items:
            repo_url = item["repository_url"]
            name = "/".join(repo_url.rstrip("/").split("/")[-2:])
            seen_repo_names.add(name)
        if len(items) < 100:
            break
        page += 1

    for name in seen_repo_names:
        if name in repos:
            repos[name]["kinds"].add("comment")
            continue
        try:
            repo_info = gh_api(f"repos/{name}")
        except subprocess.CalledProcessError:
            continue
        if repo_info.get("private"):
            continue
        repos[name] = {
            "url": repo_info["html_url"],
            "stars": repo_info["stargazers_count"],
            "kinds": {"comment"},
        }


def main():
    repos = {}
    collect_direct_contributions(repos)
    collect_comment_contributions(repos)

    ranked = sorted(repos.items(), key=lambda kv: kv[1]["stars"], reverse=True)

    lines = []
    for name, info in ranked:
        is_own = name.startswith(f"{USERNAME}/")
        tags = []
        if not is_own:
            tags.append("external")
        if info["kinds"] == {"comment"}:
            tags.append("commented only")
        tag_str = f" *({', '.join(tags)})*" if tags else ""
        lines.append(f"- [{name}]({info['url']}) ⭐ {info['stars']}{tag_str}")

    body = "\n".join(lines) if lines else "_No public contribution activity in the past year yet._"

    block = (
        "<!-- CONTRIBUTIONS:START -->\n"
        f"{body}\n"
        "<!-- CONTRIBUTIONS:END -->"
    )

    with open(README_FILE) as f:
        readme = f.read()

    new_readme = re.sub(
        r"<!-- CONTRIBUTIONS:START -->.*<!-- CONTRIBUTIONS:END -->",
        block,
        readme,
        flags=re.DOTALL,
    )

    with open(README_FILE, "w") as f:
        f.write(new_readme)

    print(f"Contribution repos found: {len(ranked)}")


if __name__ == "__main__":
    main()
