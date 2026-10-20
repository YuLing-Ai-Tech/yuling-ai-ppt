"""风格契约门禁：放映内核（runtime/）和通用组件（components/）只认令牌，颜色字面量只许写在风格目录里。"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GENERIC_FILES = sorted([*REPO.glob("runtime/*.css"), *REPO.glob("runtime/*.js"), *REPO.glob("components/**/*.css"),
                       *REPO.glob("components/**/*.js")])
COLOR_LITERAL = re.compile(r"#[0-9A-Fa-f]{3,8}\b|\b(?:rgb|rgba|hsl|hsla|oklch|oklab|lab|lch|hwb|color-mix|color)\(")
# 16 个基本色名（transparent、currentColor 允许）；只扫 .css，JS 里的 red 等词可能是字符串或注释
BASIC_COLOR_NAME = re.compile(
    r"(?<![-\w])(?:black|silver|gray|white|maroon|red|purple|fuchsia|green|lime|olive|yellow|navy|blue|teal|aqua)(?![-\w])")
# 设计 §3.1：具体色名是苹果风私有，通用组件不许用
APPLE_PRIVATE_TOKEN = re.compile(r"var\(--(?:red|pink|orange|yellow|green|teal|indigo|purple|cyan)\)")
# mask 只取颜色的透明度，#000 在这里表示"不透明"，不是配色
# 只豁免属性名在声明开头（行首、{ 或 ; 之后）的 mask 声明，到下一个 ; 或 } 为止
MASK_DECLARATION = re.compile(r"(?:(?<=[{;])|^)\s*(?:-webkit-)?mask[a-z-]*\s*:[^;}]*")
CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)


def blank_css_comments(css_text):
    """注释内容换成空格、保留换行，行号不变。"""
    return CSS_COMMENT.sub(lambda match: re.sub(r"[^\n]", " ", match.group(0)), css_text)


# 通用层（runtime/、components/）引用的全部 var(--名字)：第二风格必须提供的样式契约。
# 通用层新增或删除引用时，同步改这里；苹果风私有名（--red、--pink、--g-* 等）不许进来。
CONTRACT_TOKENS = {
    "accent", "accent-glow", "accent-soft", "bad", "bad-line", "bad-soft", "bg", "c1", "c2", "code-bg",
    "code-comment", "code-ink", "code-keyword", "code-ok", "code-string", "d", "dev-ink", "ease", "ease-io",
    "font", "glass-bg", "glass-border", "i", "ink", "ink-2", "ink-3", "l", "lift", "line", "line-strong",
    "live-ink", "live-line", "live-soft", "night", "night-ink", "night-ink-2", "on-color", "on-color-soft",
    "panel-bg", "planned", "qr-bg", "radius-block", "radius-card", "radius-panel", "radius-pill",
    "radius-thumb", "rx", "ry", "shadow", "shadow-lift", "space-grid", "space-grid-dense", "space-inline",
    "space-section", "space-split", "space-stack", "spring", "surface", "surface-2", "table-bg", "text-body",
    "text-caption", "text-emphasis", "text-heading", "text-icon", "text-label", "text-name", "text-quote",
    "text-small", "text-stat", "text-timer", "theme", "theme-solid",
    # M3 图元（设计 §3.1）：五类连线色、流速、网格线、等宽字、压暗透明度、分类色、图元小字与小圆角
    "flow-sync", "flow-async", "flow-data", "flow-human", "flow-tele", "flow-speed", "grid-line", "mono", "dim-opacity",
    "cat-1", "cat-2", "cat-3", "cat-4", "cat-5", "cat-6", "cat-7", "cat-8", "text-tag", "radius-tag",
    # M3 图元与分步的运行时变量（见下方 RUNTIME_SET_TOKENS）
    "kind-color", "tone", "cell-w", "cell-h", "len", "delay", "step-delay", "packet-phase",
}
# 不由风格样式表定义的变量，各有运行时的设置者
RUNTIME_SET_TOKENS = {
    "d",     # 课件页 HTML 里行内 style="--d:N" 由作者写，动画错峰序号
    "i",     # runtime/page-map.js 给每张缩略图 tile.style.setProperty("--i", ...)
    "l",     # runtime/deck.js 给标题每一行 span 写行内 style="--l:N"
    "lift",  # components/blocks/card.css、wall.css 在组件自己的规则里局部定义
    "rx",    # styles/苹果风/pointer-light.js 的 setProperty，卡片倾斜角
    "ry",    # 同上
    "kind-color",    # components/diagram/edges.css 按 data-kind 局部定义（取 --flow-*）
    "tone",          # components/diagram/diagram.css 在 .dg 和 [data-tone] 上局部定义（取 --accent、--cat-N）
    "cell-w",        # components/diagram/render.js 按图区宽度 / 列数写在 .dg 上
    "cell-h",        # 同上，高度 / 行数
    "len",           # components/diagram/render.js 写连线长度（像素，不带单位）
    "delay",         # components/diagram/render.js 写每个图元的登场先后
    "step-delay",    # runtime/steps.js 一次揭示全部步骤时写每步的错峰
    "packet-phase",  # components/diagram/render.js 写数据包在线上的起始相位（0～1）
}
# 由主题按页给值：只要求出现在 themes.css 的 [data-theme] 规则里
THEME_TOKENS = {"theme", "theme-solid", "c1", "c2", "c3"}
CSS_VAR_REFERENCE = re.compile(r"var\(--([\w-]+)")


def test_generic_layers_only_use_contract_tokens():
    used_tokens = set()
    for path in GENERIC_FILES:
        source_text = path.read_text(encoding="utf-8")
        if path.suffix == ".css":
            source_text = blank_css_comments(source_text)
        used_tokens |= set(CSS_VAR_REFERENCE.findall(source_text))
    assert sorted(used_tokens - CONTRACT_TOKENS) == []


def test_apple_tokens_define_the_contract():
    apple_css = "\n".join(blank_css_comments(path.read_text(encoding="utf-8")) for path in (REPO / "styles" / "苹果风").glob("*.css"))
    themes_css = (REPO / "styles" / "苹果风" / "themes.css").read_text(encoding="utf-8")
    missing = []
    for name in sorted(CONTRACT_TOKENS - RUNTIME_SET_TOKENS):
        defined_in = themes_css if name in THEME_TOKENS else apple_css
        if not re.search(rf"--{re.escape(name)}\s*:", defined_in):
            missing.append(name)
    assert missing == []


def color_offenders():
    offenders = []
    for path in GENERIC_FILES:
        source_text = path.read_text(encoding="utf-8")
        is_css = path.suffix == ".css"
        if is_css:
            source_text = blank_css_comments(source_text)
        for line_number, line in enumerate(source_text.splitlines(), 1):
            checked_text = MASK_DECLARATION.sub("", line)
            found = [*COLOR_LITERAL.finditer(checked_text), *APPLE_PRIVATE_TOKEN.finditer(checked_text)]
            if is_css:
                found += BASIC_COLOR_NAME.finditer(checked_text)
            for match in found:
                offenders.append(f"{path.relative_to(REPO)}:{line_number} {match.group(0)}")
    return offenders


def test_generic_layers_have_no_color_literals():
    assert GENERIC_FILES, "通用文件 glob 没匹配到任何文件"
    assert color_offenders() == []


GENERIC_CSS = [path for path in GENERIC_FILES if path.suffix == ".css"]
SIZE_DECLARATION = re.compile(r"(?<![\w-])(font-size|font|border-radius|grid-gap|gap|row-gap|column-gap)\s*:\s*([^;}]+)")
PX_LITERAL = re.compile(r"(?<![\w.])\d+(?:\.\d+)?px")
# 只出现一次、没有对应角色的尺寸留在原处，每条写明是什么；新增字面量要么用令牌，要么在这里登记理由
SIZE_ALLOWLIST = {
    ("runtime/nav.css", "gap", "14px"),               # 品牌区：logo 与文字
    ("runtime/nav.css", "gap", "16px"),               # 翻页按钮之间
    ("runtime/nav.css", "gap", "18px"),               # 页码与进度条
    ("runtime/nav.css", "border-radius", "10px"),     # 品牌 logo
    ("runtime/nav.css", "border-radius", "3px"),      # 进度条
    ("runtime/page-map.css", "gap", "12px"),          # 地图按钮：图标与文字
    ("runtime/page-map.css", "gap", "3px"),           # 地图按钮的九宫格小点
    ("runtime/page-map.css", "border-radius", "2px"), # 九宫格小点
    ("runtime/page-map.css", "gap", "22px"),          # 地图标题与说明
    ("runtime/page-map.css", "font-size", "44px"),    # 地图标题
    ("runtime/page-map.css", "gap", "30px"),          # 缩略图行距
    ("runtime/page-map.css", "gap", "24px"),          # 缩略图列距
    ("runtime/page-map.css", "font-size", "19px"),    # 缩略图标题
    ("runtime/page-map.css", "font-size", "15px"),    # 缩略图副标题
    ("components/blocks/icon.css", "border-radius", "22px"),   # 图标块
    ("components/blocks/flow.css", "font-size", "19px"),       # 流程节点小字
    ("components/blocks/ladder.css", "font-size", "30px"),     # 阶梯标题
    ("components/blocks/ladder.css", "font-size", "40px"),     # 阶梯序号
    ("components/blocks/ladder.css", "border-radius", "12px"), # 阶梯底角
    ("components/blocks/layers.css", "gap", "14px"),           # 六层之间
    ("components/blocks/qr.css", "border-radius", "34px"),     # 二维码卡
    ("components/blocks/qr.css", "border-radius", "14px"),     # 二维码图与占位
    ("components/blocks/table.css", "font-size", "21px"),      # 表头
    ("components/blocks/toolcard.css", "gap", "12px"),         # 工具卡：缩略图与文字
    ("components/layouts/chapter.css", "gap", "18px"),         # 章节页 meta 标签之间
}


def size_literals():
    """返回 (未登记的位置列表, 出现过的 (文件, 属性, 字面量) 集合)。"""
    unlisted, seen = [], set()
    for path in GENERIC_CSS:
        relative_path = str(path.relative_to(REPO))
        css_text = blank_css_comments(path.read_text(encoding="utf-8"))
        for line_number, line in enumerate(css_text.splitlines(), 1):
            for declaration in SIZE_DECLARATION.finditer(line):
                for literal in PX_LITERAL.findall(declaration.group(2)):
                    key = (relative_path, declaration.group(1), literal)
                    seen.add(key)
                    if key not in SIZE_ALLOWLIST:
                        unlisted.append(f"{relative_path}:{line_number} {declaration.group(1)}: {literal}")
    return unlisted, seen


def test_generic_sizes_use_tokens():
    unlisted, _ = size_literals()
    assert unlisted == []


def test_size_allowlist_has_no_stale_entries():
    _, seen = size_literals()
    assert sorted(SIZE_ALLOWLIST - seen) == []
