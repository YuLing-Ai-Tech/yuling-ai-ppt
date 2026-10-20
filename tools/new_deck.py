"""新建课件工程：按风格清单复制引擎快照 + 起步页 + deck.json。目标目录必须不存在或为空。"""

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SNAPSHOT_TOOLS = ("tools/build_deck.py", "tools/preview_slides.py")


def parse_args():
    parser = argparse.ArgumentParser(description="新建一套 HTML 课件工程")
    parser.add_argument("target", type=Path)
    parser.add_argument("--title", required=True)
    parser.add_argument("--style", default="苹果风")
    return parser.parse_args()


def ensure_empty_target(target):
    if target.exists() and any(target.iterdir()):
        sys.exit(f"目标目录非空，拒绝覆盖：{target}")
    target.mkdir(parents=True, exist_ok=True)


def copy_relative(relative_path, target):
    destination = target / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / relative_path, destination)


def copy_engine_snapshot(style, target):
    manifest_path = f"styles/{style}/manifest.json"
    manifest = json.loads((REPO / manifest_path).read_text())
    for relative_path in [*manifest["css"], *manifest["js"], manifest["backdrop"], manifest_path, *SNAPSHOT_TOOLS]:
        copy_relative(relative_path, target)


def copy_templates(style, target, title):
    template_dir = REPO / "templates" / style
    shutil.copytree(template_dir / "slides", target / "slides")
    (target / "styles").mkdir(exist_ok=True)
    config = json.loads((template_dir / "deck.json").read_text())
    config.update({"title": title, "style": style, "output": f"{title.replace('/', '-')}.html"})
    (target / "deck.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")


def main():
    args = parse_args()
    target = args.target.expanduser().resolve()
    if not (REPO / "styles" / args.style / "manifest.json").exists():
        sys.exit(f"没有这个风格：{args.style}")
    ensure_empty_target(target)
    copy_engine_snapshot(args.style, target)
    copy_templates(args.style, target, args.title)
    print(f"已新建：{target}（风格：{args.style}）")
    print(f"下一步：cd {target} && python3 tools/build_deck.py --deck . --engine-root .")


if __name__ == "__main__":
    main()
