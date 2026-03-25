#!/usr/bin/env python3
"""
Push bot changes to GitHub via REST API.
Usage: python3 push_to_github.py "commit message"
"""
import os
import sys
import base64
import json
import urllib.request
import urllib.error

OWNER = "karlosdzunior-hub"
REPO  = "doll"
BRANCH = "main"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

BOT_DIR = os.path.dirname(os.path.abspath(__file__))


def api(method: str, path: str, data=None):
    url = f"https://api.github.com{path}"
    headers = {
        "Authorization": f"token {TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode()}")
        raise


def get_sha(branch=BRANCH):
    ref = api("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/{branch}")
    return ref["object"]["sha"]


def get_tree_sha(commit_sha):
    commit = api("GET", f"/repos/{OWNER}/{REPO}/git/commits/{commit_sha}")
    return commit["tree"]["sha"]


def create_blob(content: str):
    blob = api("POST", f"/repos/{OWNER}/{REPO}/git/blobs", {
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "encoding": "base64"
    })
    return blob["sha"]


def create_tree(base_tree_sha, file_changes: list):
    tree = api("POST", f"/repos/{OWNER}/{REPO}/git/trees", {
        "base_tree": base_tree_sha,
        "tree": file_changes
    })
    return tree["sha"]


def create_commit(message, tree_sha, parent_sha):
    commit = api("POST", f"/repos/{OWNER}/{REPO}/git/commits", {
        "message": message,
        "tree": tree_sha,
        "parents": [parent_sha]
    })
    return commit["sha"]


def update_ref(commit_sha, branch=BRANCH):
    api("PATCH", f"/repos/{OWNER}/{REPO}/git/refs/heads/{branch}", {
        "sha": commit_sha,
        "force": False
    })


def push_files(files_in_bot_dir: list, commit_message: str):
    """Push files to GitHub. files_in_bot_dir = list of relative paths from bot dir."""
    if not TOKEN:
        print("❌ GITHUB_TOKEN не задан!")
        return False

    print(f"🔄 Пушим {len(files_in_bot_dir)} файлов в {OWNER}/{REPO}:{BRANCH}")

    current_sha = get_sha()
    tree_sha = get_tree_sha(current_sha)

    tree_entries = []
    for rel_path in files_in_bot_dir:
        abs_path = os.path.join(BOT_DIR, rel_path)
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        blob_sha = create_blob(content)
        # GitHub path = путь в репозитории (от корня)
        repo_path = os.path.join("artifacts/tg-bot", rel_path).replace("\\", "/")
        tree_entries.append({
            "path": repo_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha
        })
        print(f"  ✅ {repo_path}")

    new_tree_sha = create_tree(tree_sha, tree_entries)
    new_commit_sha = create_commit(commit_message, new_tree_sha, current_sha)
    update_ref(new_commit_sha)

    print(f"✅ Запушено! Коммит: {new_commit_sha[:8]}")
    return True


if __name__ == "__main__":
    message = sys.argv[1] if len(sys.argv) > 1 else "bot: update"
    files = [
        "bot.py",
        "handlers/main.py",
    ]
    push_files(files, message)
