"""把放映时拖动后保存的位置写回课件源文件（Q-017 D2 形态 B）。

用法：python3 tools/apply_positions.py --deck <课件目录> <位置文件.json>
位置文件由放映页"拖动 → 保存位置"生成（components/diagram/drag.js）：
  {"format": "yuling-positions-1", "deck": 标题, "moves": [{"page": 页码, "source": "03_x.html", "diagram": 0, "id": "api", "at": "1.5 2 4 1.8", "was": "1 2 4 1.8"}]}
每条按 source（slides/ 下的文件名）→ 该文件里第 diagram 个 .dg（从 0 数）→ 其中 data-id 等于 id 的元素，改写它的 data-at
（树图、循环图里原来没写 data-at 的节点就补上，之后它固定在拖到的位置）。
was 是保存时源文件里该节点 data-at 的原值（源里没写、由树图/循环图自动排的记 ""）。写回前逐条核对源文件当前值，
不一致（保存后改过片段、插过图）就报错、不写；deck 要和 deck.json 的 title 一致。
有任何一条有问题（找不到文件、第几个图、id；格式不对；was 对不上；同一目标出现两次），全部列出、退出码 1，一个文件都不改；
写盘前所有文件都先在内存里改好并核对。写回后照常 build_deck + preview_slides 检查。
"""

import argparse
import html
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

POSITIONS_FORMAT = "yuling-positions-1"
FOUR_NUMBERS = re.compile(r"^\s*-?\d+(\.\d+)?(\s+-?\d+(\.\d+)?){3}\s*$")
TAG_NAME = re.compile(r"<[^\s/>]+")
ATTRIBUTE = re.compile(r"""[\s/]*([^\s"'>/=][^\s"'/>=]*)(?:\s*=\s*("[^"]*"|'[^']*'|[^\s>]*))?""")


def read_source(path):
    """按原样读（不转换换行），写回时才能保持 CRLF 不变。"""
    with open(path, encoding="utf-8", newline="") as source_file:
        return source_file.read()


def write_source(path, text):
    with open(path, "w", encoding="utf-8", newline="") as source_file:
        source_file.write(text)


def data_at_attribute(start_tag):
    """返回 (data-at 的值或 None, 属性名起到值止在标签里的位置)；只认真正的属性名，不看别的属性值里的文字。"""
    position = TAG_NAME.match(start_tag).end()
    while True:
        match = ATTRIBUTE.match(start_tag, position)
        if not match or match.end() == position:
            return None, None
        if match.group(1).lower() == "data-at":
            return html.unescape((match.group(2) or "").strip("\"'")), (match.start(1), match.end())
        position = match.end()


class DiagramElementFinder(HTMLParser):
    """按出现顺序记下每个 .dg 里带 data-id 的元素：[{id: (起始标签在文件里的偏移, 起始标签原文)}]。<script> 里的内容不解析。
    行偏移按 "\\n" 数，和 HTMLParser 数行的方式一致（str.splitlines 会在 \\x0c、\\u2028 等处断行，偏移就错了）。"""

    def __init__(self, source_text):
        super().__init__(convert_charrefs=True)
        self.line_offsets = [0]
        for line in source_text.split("\n"):
            self.line_offsets.append(self.line_offsets[-1] + len(line) + 1)
        self.diagrams = []
        self._open_tag = None
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if self._open_tag is None:
            if "dg" in classes:
                self._open_tag, self._depth = tag, 1
                self.diagrams.append({})
            return
        if tag == self._open_tag:
            self._depth += 1
        if attributes.get("data-id"):
            line, column = self.getpos()
            self.diagrams[-1][attributes["data-id"]] = (self.line_offsets[line - 1] + column, self.get_starttag_text())

    def handle_endtag(self, tag):
        if tag == self._open_tag:
            self._depth -= 1
            if self._depth == 0:
                self._open_tag = None


def with_data_at(start_tag, at):
    replacement = f'data-at="{html.escape(at)}"'
    _, span = data_at_attribute(start_tag)
    if span:
        return start_tag[: span[0]] + replacement + start_tag[span[1]:]
    closing = "/>" if start_tag.endswith("/>") else ">"
    return start_tag[: -len(closing)] + " " + replacement + closing


def move_field_problems(move):
    """一条 move 的字段是否齐全、类型对；返回问题文字列表。"""
    if not isinstance(move, dict):
        return [f"这一条不是对象：{move!r}"]
    problems = []
    for name in ("source", "id", "was"):
        if name not in move:
            problems.append(f"缺少 {name}" + ("（旧版页面保存的文件，请用新版放映页重新保存）" if name == "was" else ""))
        elif not isinstance(move[name], str):
            problems.append(f"{name} 要是文字：{move[name]!r}")
    if not isinstance(move.get("at"), str) or not FOUR_NUMBERS.match(move["at"]):
        problems.append(f"at 要写 4 个数（列 行 宽 高）：{move.get('at')!r}")
    if not isinstance(move.get("diagram"), int) or isinstance(move.get("diagram"), bool):
        problems.append(f"diagram 要是整数：{move.get('diagram')!r}")
    return problems


def planned_edits(slides_dir, moves):
    """返回 ({文件: [(偏移, 旧标签, 新标签)…]}, [问题…])。来源文件只认 slides/ 下的文件名；图的序号从 0 数，报错时同时给出"第几个"。"""
    edits, problems, finders, seen = {}, [], {}, {}
    for number, move in enumerate(moves, 1):
        field_problems = move_field_problems(move)
        if field_problems:
            problems.extend(f"第 {number} 条：{reason}" for reason in field_problems)
            continue
        where = f"第 {move.get('page', '?')} 页 {move['id']}"
        source = move["source"]
        if "\0" in source:
            problems.append(f"{where}：来源文件名不合法")
            continue
        path = slides_dir / source
        if source and path.resolve().parent != slides_dir.resolve():
            problems.append(f"{where}：来源文件 {source} 不在 slides/ 里，拒绝写入")  # 位置文件可能是别人转发来的
            continue
        if not source or not path.is_file():
            problems.append(f"{where}：来源文件 {source or '（空，课件要用新版 build_deck 重新构建）'} 不存在")
            continue
        if path not in finders:
            try:
                text = read_source(path)
            except UnicodeDecodeError:
                problems.append(f"{where}：来源文件 {source} 不是 UTF-8，没法读")
                finders[path] = None
                continue
            finders[path] = DiagramElementFinder(text)
            finders[path].feed(text)
        if finders[path] is None:
            continue
        diagrams = finders[path].diagrams
        index = move["diagram"]
        if not 0 <= index < len(diagrams):
            problems.append(f"{where}：{path.name} 里没有第 {index + 1} 个图（序号 {index}，共 {len(diagrams)} 个）")
        elif move["id"] not in diagrams[index]:
            problems.append(f"{where}：{path.name} 第 {index + 1} 个图（序号 {index}）里没有 data-id={move['id']}")
        elif (path, index, move["id"]) in seen:
            problems.append(f"{where}（第 {number} 条）：和第 {seen[(path, index, move['id'])]} 条是同一个节点（{path.name} 序号 {index} 的 {move['id']}），重复出现")
        else:
            seen[(path, index, move["id"])] = number
            offset, start_tag = diagrams[index][move["id"]]
            current = data_at_attribute(start_tag)[0] or ""
            if " ".join(current.split()) != " ".join(move["was"].split()):
                problems.append(f"{where}（第 {number} 条）：{path.name} 第 {index + 1} 个图（序号 {index}）里 data-id={move['id']} 的 data-at 和保存时不一致："
                                f"保存时是 {move['was']!r}，现在是 {current!r}（保存后改过这个文件？请重新拖动并保存）")
                continue
            edits.setdefault(path, []).append((offset, start_tag, with_data_at(start_tag, move["at"])))
    return edits, problems


def deck_title(deck_dir):
    try:
        return json.loads((Path(deck_dir) / "deck.json").read_text(encoding="utf-8")).get("title")
    except (OSError, ValueError):
        return None


def apply_positions(deck_dir, positions_path):
    """写回；返回 (改了几处, 问题列表)。有问题时一个文件都不改；所有文件先在内存里改好并核对，全部成功才落盘。"""
    try:
        positions = json.loads(Path(positions_path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return 0, [f"位置文件读不了：{error}"]
    if not isinstance(positions, dict) or positions.get("format") != POSITIONS_FORMAT:
        return 0, [f"位置文件格式不是 {POSITIONS_FORMAT}：{positions.get('format') if isinstance(positions, dict) else positions}"]
    expected_title = deck_title(deck_dir)
    if expected_title and " ".join(str(positions.get("deck")).split()) != " ".join(expected_title.split()):
        return 0, [f"位置文件来自课件 {positions.get('deck')}，这个课件是 {expected_title}"]
    moves = positions.get("moves")
    if not isinstance(moves, list):
        return 0, ["位置文件里 moves 不是列表"]
    edits, problems = planned_edits(Path(deck_dir) / "slides", moves)
    if problems:
        return 0, problems
    new_texts = {}
    for path, file_edits in edits.items():
        text = read_source(path)
        for offset, old_tag, new_tag in sorted(file_edits, reverse=True):  # 从后往前改，前面的偏移不变
            if text[offset:offset + len(old_tag)] != old_tag:  # 不用 assert：python -O 会把它去掉
                raise RuntimeError(f"{path.name} 在读取后被改过，第 {offset} 个字符处对不上，没有写回")
            text = text[:offset] + new_tag + text[offset + len(old_tag):]
        new_texts[path] = text
    for path, text in new_texts.items():
        write_source(path, text)
    return sum(len(file_edits) for file_edits in edits.values()), []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deck", type=Path, required=True, help="课件目录（含 slides/）")
    parser.add_argument("positions", type=Path, help="放映页保存的位置文件（.json）")
    args = parser.parse_args()
    changed, problems = apply_positions(args.deck, args.positions)
    if problems:
        sys.exit("没有写回，位置文件里有问题：\n" + "\n".join(problems))
    print(f"写回 {changed} 处 data-at；请重新构建并跑 preview_slides.py 检查")


if __name__ == "__main__":
    main()
