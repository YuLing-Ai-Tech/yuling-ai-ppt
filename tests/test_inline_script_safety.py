"""清单里的 JS 拼进成品的同一个 <script>（tools/build_deck.py）：任何一个文件里出现结束标签（或 `<script`、`<!--`）的字面量，HTML 解析器就在那里把脚本截断，
后面的代码全部丢失、不报 JS 错误，整份课件静默启动失败（写教师包计划时实测过）。纯文本检查，不起浏览器。"""
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# 结束标签会直接截断脚本；`<script` 加 `<!--` 会让解析器进入 double-escaped 状态，吞掉真正的结束标签
SCRIPT_BREAKERS = re.compile(r"</script|<script|<!--", re.I)


def test_no_manifest_script_contains_a_script_tag_or_html_comment_opener():
    offenders = []
    for manifest_path in sorted((REPO / "styles").glob("*/manifest.json")):
        for relative_path in json.loads(manifest_path.read_text(encoding="utf-8"))["js"]:
            for line_number, line in enumerate((REPO / relative_path).read_text(encoding="utf-8").splitlines(), 1):
                if SCRIPT_BREAKERS.search(line):
                    offenders.append(f"{relative_path}:{line_number}")
    assert offenders == []
