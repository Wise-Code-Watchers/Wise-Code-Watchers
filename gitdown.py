#!/usr/bin/env python3
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def run(cmd, cwd=None, capture=True):
    """Run a command, raise on error."""
    if capture:
        p = subprocess.run(cmd, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return p.stdout
    else:
        subprocess.run(cmd, cwd=cwd, check=True)


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_branch_name(name: str) -> str:
    # keep it filesystem friendly
    return name.replace("/", "__")


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            # If corrupted, keep a backup and reset
            bak = path.with_suffix(path.suffix + ".bak")
            shutil.copy2(path, bak)
            return default
    return default


def save_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def get_remote_heads(repo_url: str):
    """
    Returns dict: branch -> sha from `git ls-remote --heads`.
    """
    out = run(["git", "ls-remote", "--heads", repo_url])
    heads = {}
    for line in out.strip().splitlines():
        sha, ref = line.split("\t", 1)
        m = re.match(r"refs/heads/(.+)$", ref.strip())
        if m:
            heads[m.group(1)] = sha.strip()
    return heads


def ensure_cache_repo(cache_dir: Path, repo_url: str):
    """
    Create a local cache git repo to use `git archive` quickly.
    Uses fetch with depth=1 per branch when needed.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    git_dir = cache_dir / ".git"
    if not git_dir.exists():
        run(["git", "init", "-q", str(cache_dir)], capture=False)
        run(["git", "-C", str(cache_dir), "remote", "add", "origin", repo_url], capture=False)
    else:
        # keep origin URL up-to-date
        run(["git", "-C", str(cache_dir), "remote", "set-url", "origin", repo_url], capture=False)


def fetch_branch_depth1(cache_dir: Path, branch: str):
    """
    Fetch only branch head commit with depth=1 into refs/remotes/origin/<branch>.
    """
    run(
        [
            "git", "-C", str(cache_dir),
            "fetch", "-q", "--depth", "1", "--no-tags", "origin",
            f"refs/heads/{branch}:refs/remotes/origin/{branch}",
        ],
        capture=False
    )


def export_commit_snapshot(cache_dir: Path, sha: str, out_dir: Path):
    """
    Export the given commit SHA from cache repo to out_dir via git archive | tar.
    """
    tmp = out_dir.with_name(out_dir.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)

    # Use a pipe: git archive <sha> | tar -x -C tmp
    # We rely on 'tar' existing (Linux/macOS/Git Bash).
    p1 = subprocess.Popen(
        ["git", "-C", str(cache_dir), "archive", sha],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False
    )
    p2 = subprocess.Popen(
        ["tar", "-x", "-C", str(tmp)],
        stdin=p1.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False
    )
    p1.stdout.close()
    _, err2 = p2.communicate()
    _, err1 = p1.communicate()

    if p1.returncode != 0:
        raise RuntimeError(f"git archive failed: {err1.decode(errors='ignore')}")
    if p2.returncode != 0:
        raise RuntimeError(f"tar extract failed: {err2.decode(errors='ignore')}")

    # swap in atomically-ish
    if out_dir.exists():
        shutil.rmtree(out_dir)
    tmp.rename(out_dir)


def get_repo_name_from_url(url: str) -> str:
    """
    Extract the repository name from the URL.
    E.g. https://github.com/org/repo.git -> repo
    E.g. https://bgithub.xyz/Wise-Code-Watchers/sentry-wcw -> sentry-wcw
    """
    match = re.match(r".*/([^/]+)(?:\.git)?$", url)
    if match:
        return match.group(1)
    raise ValueError(f"Invalid URL format: {url}")


def main():
    if len(sys.argv) < 2:
        print("Usage: ./2.py <repo_url> [output_dir]", file=sys.stderr)
        sys.exit(1)

    repo_url = sys.argv[1]
    repo_name = get_repo_name_from_url(repo_url)
    out_dir = Path(sys.argv[2] if len(sys.argv) >= 3 else f"{repo_name}-snapshots")

    cache_dir = out_dir / "_cache_repo"
    branches_dir = out_dir / "branches"
    meta_file = out_dir / "branches.json"

    out_dir.mkdir(parents=True, exist_ok=True)
    branches_dir.mkdir(parents=True, exist_ok=True)

    # 1) Remote heads
    remote = get_remote_heads(repo_url)

    # 2) Local previous state map: name -> sha
    prev_list = load_json(meta_file, default=[])
    prev_map = {item.get("name"): item.get("sha") for item in prev_list if isinstance(item, dict) and item.get("name")}

    # 3) Ensure cache repo exists
    ensure_cache_repo(cache_dir, repo_url)

    results = []
    # stable order
    for name in sorted(remote.keys()):
        sha = remote[name]
        prev_sha = prev_map.get(name)
        safe = safe_branch_name(name)
        path_rel = f"branches/{safe}"
        snap_path = branches_dir / safe

        updated = (prev_sha != sha)

        if not updated and snap_path.exists():
            # no change and snapshot exists: skip
            results.append({
                "name": name,
                "safe_name": safe,
                "sha": sha,
                "prev_sha": prev_sha,
                "updated": False,
                "path": path_rel,
                "time": now_utc(),
            })
            print(f"==> {name}: unchanged, skip ({sha[:12]})")
            continue

        # If snapshot missing, we should download even if prev_sha matches (rare but possible)
        if not snap_path.exists():
            updated = True

        print(f"==> {name}: updating to {sha[:12]} (prev {str(prev_sha)[:12] if prev_sha else 'None'})")

        # fetch + export
        fetch_branch_depth1(cache_dir, name)
        export_commit_snapshot(cache_dir, sha, snap_path)

        results.append({
            "name": name,
            "safe_name": safe,
            "sha": sha,
            "prev_sha": prev_sha,
            "updated": True,
            "path": path_rel,
            "time": now_utc(),
        })

    save_json(meta_file, results)
    print(f"\nDone.\nSnapshots: {branches_dir}\nMetadata:  {meta_file}")


if __name__ == "__main__":
    main()
