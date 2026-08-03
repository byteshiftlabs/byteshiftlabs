#!/usr/bin/env python3
"""Render a list of repos (mine or anyone else's) I've contributed to in the
past year -- commits, PRs, or issues -- via GitHub's GraphQL API.

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


def main():
    data = gh_graphql(QUERY, login=USERNAME)
    collection = data["data"]["user"]["contributionsCollection"]

    repos = {}
    for key in (
        "commitContributionsByRepository",
        "pullRequestContributionsByRepository",
        "issueContributionsByRepository",
    ):
        for entry in collection[key]:
            repo = entry["repository"]
            if repo["isPrivate"]:
                continue
            repos[repo["nameWithOwner"]] = repo

    ranked = sorted(repos.values(), key=lambda r: r["stargazerCount"], reverse=True)

    lines = []
    for repo in ranked:
        is_own = repo["nameWithOwner"].startswith(f"{USERNAME}/")
        tag = "" if is_own else " *(external)*"
        lines.append(
            f"- [{repo['nameWithOwner']}]({repo['url']}) "
            f"⭐ {repo['stargazerCount']}{tag}"
        )

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
