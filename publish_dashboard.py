import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DASHBOARD_PATH = "docs/index.html"


def run(*args, capture_output=False):
    return subprocess.run(
        list(args),
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=capture_output,
    )


def has_dashboard_changes():
    result = run("git", "status", "--porcelain", DASHBOARD_PATH, capture_output=True)
    return bool(result.stdout.strip())


def pending_commit_count():
    result = run("git", "rev-list", "--count", "origin/main..HEAD", capture_output=True)
    return int(result.stdout.strip() or "0")


def push_pending_commits():
    pending = pending_commit_count()
    if not pending:
        return

    print(f"Retrying {pending} pending commit(s) before creating another dashboard commit.")
    run("git", "push", "origin", "main")


def main():
    # A failed push used to leave one commit behind, then every heartbeat
    # created another commit before retrying. Retry the existing commit first
    # so an outage cannot grow the local branch without bound.
    push_pending_commits()

    if not has_dashboard_changes():
        print("Dashboard unchanged.")
        return

    run("git", "add", DASHBOARD_PATH)
    run("git", "commit", "-m", "Update trading dashboard")
    run("git", "push", "origin", "main")
    print("Dashboard published.")


if __name__ == "__main__":
    main()
