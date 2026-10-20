"""手写程序文件行数门禁：超过 800 行的文件列出来，退出码 1。"""

import subprocess
import sys
from pathlib import Path

LIMIT = 800
CHECKED_SUFFIXES = {".py", ".js", ".css", ".html", ".sh"}
EXCLUDED_PREFIXES = ("examples/甬舟94/images/",)


def tracked_and_new_files(repo):
    listing = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             cwd=repo, capture_output=True, check=True).stdout.decode("utf-8")
    return [path for path in listing.split("\0") if path]


def over_limit(repo, limit=LIMIT):
    offenders = []
    for relative_path in tracked_and_new_files(repo):
        if Path(relative_path).suffix not in CHECKED_SUFFIXES or relative_path.startswith(EXCLUDED_PREFIXES):
            continue
        line_count = len((Path(repo) / relative_path).read_text(encoding="utf-8").splitlines())
        if line_count > limit:
            offenders.append((relative_path, line_count))
    return offenders


def main():
    repo = Path(__file__).resolve().parent.parent
    offenders = over_limit(repo)
    for relative_path, line_count in offenders:
        print(f"超过 {LIMIT} 行：{relative_path}（{line_count} 行）")
    print("行数检查：" + ("通过" if not offenders else f"{len(offenders)} 个文件超限"))
    sys.exit(1 if offenders else 0)


if __name__ == "__main__":
    main()
