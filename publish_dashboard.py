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


def main():
    if not has_dashboard_changes():
        print("Dashboard unchanged.")
        return

    run("git", "add", DASHBOARD_PATH)
    run("git", "commit", "-m", "Update trading dashboard")
    run("git", "push", "origin", "main")
    print("Dashboard published.")


if __name__ == "__main__":
    main()
