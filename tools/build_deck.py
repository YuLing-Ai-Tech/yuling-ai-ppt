"""把 slides/ 下的片段、styles/ 样式、scripts/ 脚本和图片拼成可离线放映的单文件 HTML。

用法：python3 tools/build_deck.py --deck <课件目录> [--engine-root <引擎根目录>] [--only 03a 03b] [--out 路径]
配置：<课件目录>/deck.json
  title       标题（浏览器标签页）
  logo        导航栏左下角图标路径，可省略；省略则不显示图标
  brand       导航栏品牌文字，默认 "YuLing AI"
  output      输出文件名，默认 "<title>.html"，相对课件目录
  image_root  {{img:相对路径}} 的根目录，默认课件目录
  style       风格名，默认 "苹果风"；读 <引擎根目录>/styles/<风格>/manifest.json（css / js / backdrop 路径，相对引擎根目录）
片段里写 <img src="{{img:截图/01.png}}">，构建时压成 JPEG 内嵌；路径含"二维码"或"qr"的走无损 PNG。
片段里的 <!-- 注释 --> 构建时删掉，不进成品（讲师备注、待确认事项不会泄到放映文件里）。
图元引用检查（设计 §4.5 的构建期部分）：每页 data-in 指向的容器、连线 data-from / data-to 指向的节点必须存在，data-id 不许重复；
不满足就报出页码和 id、退出码 1。重叠、出界、标签压节点要量尺寸，在 preview_slides.py 里查。
每页 <section class="slide…"> 构建时补上 data-source="片段文件名"（放映时拖动保存位置要用它找回源文件，见 tools/apply_positions.py）。
"""

import argparse
import base64
import html
import io
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
IMAGE_PATTERN = re.compile(r"\{\{img:([^}]+)\}\}")
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.S)
SLIDE_START_TAG = re.compile(r'<section\b[^>]*\bclass="[^"]*(?<![\w-])slide(?![\w-])[^"]*"[^>]*>')
MAX_IMAGE_WIDTH = 1400
DEFAULT_BRAND = "YuLing AI"
DEFAULT_STYLE = "苹果风"

PAGE_SHELL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
{css}
</style>
</head>
<body{body_attrs}>
<div id="viewport"><div id="stage">
{backdrop}
<div id="motion-field" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
{slides}
<div id="nav">
  <div id="brand">{logo_img}<span>{brand}</span><em id="section-label"></em></div>
  <div id="controls"><button id="prev">‹ 上一页</button><button id="play">播放</button><button id="next">下一页 ›</button></div>
  <div id="meter"><div id="bar"><i></i></div><span id="pageno"></span></div>
</div>
<div id="hint">← → 翻页 · M 页面地图 · P 自动播放 · F 全屏</div>
<button id="map-toggle" aria-label="打开页面地图"><i><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b></i>页面地图</button>
<div id="map" aria-label="全部页面">
  <header><h2>全部页面</h2><span>点任意一页直接跳转 · Esc 关闭</span></header>
  <div id="map-grid"></div>
</div>
</div></div>
<script>
{js}
</script>
</body>
</html>
"""


def load_deck_config(deck_dir):
    config_path = deck_dir / "deck.json"
    if not config_path.exists():
        sys.exit(f"缺少配置：{config_path}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    title = config.get("title") or sys.exit("deck.json 里 title 不能为空")
    return {
        "title": title,
        "brand": config.get("brand") or DEFAULT_BRAND,
        "logo": resolve_path(deck_dir, config.get("logo")),
        "output": resolve_path(deck_dir, config.get("output") or f"{title.replace('/', '-')}.html"),
        "image_root": resolve_path(deck_dir, config.get("image_root")) or deck_dir,
        "style": config.get("style") or DEFAULT_STYLE,
        "motion": config.get("motion") if isinstance(config.get("motion"), dict) else {},
    }


def motion_body_attributes(raw):
    allowed = {
        "persona": {"business", "training", "cinematic"},
        "recipe": {"precision-flow", "editorial-focus", "kinetic-classroom", "playful-cascade", "cinematic-depth", "launch-spotlight"},
        "background": {"aurora", "particles", "kinetic-grid", "spotlight", "orbit"},
        "transition": {"focus", "depth", "directional", "wipe"},
    }
    attributes = []
    for key, values in allowed.items():
        value = raw.get(key)
        if value is None:
            continue
        if value not in values:
            sys.exit(f"deck.json 里的 motion.{key} 不受支持：{value}")
        attributes.append(f'data-motion-{key}="{html.escape(value)}"')
    fingerprint = raw.get("fingerprint")
    if fingerprint is not None:
        if not re.fullmatch(r"v1:[a-f0-9]{16}", fingerprint):
            sys.exit("deck.json 里的 motion.fingerprint 格式不正确")
        attributes.append(f'data-motion-fingerprint="{fingerprint}"')
    return (" " + " ".join(attributes)) if attributes else ""


def resolve_path(base_dir, raw_path):
    if not raw_path:
        return None
    path = Path(raw_path).expanduser()
    return path if path.is_absolute() else base_dir / path


def image_data_url(image_path, max_width=MAX_IMAGE_WIDTH, image_format="JPEG"):
    from PIL import Image  # 只在压图片时才需要 Pillow，没装也能构建不含图片的课件
    image = Image.open(image_path)
    if image_format == "JPEG":
        image = image.convert("RGB")
    if image.width > max_width:
        image = image.resize((max_width, round(image.height * max_width / image.width)), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format=image_format, **({"quality": 82} if image_format == "JPEG" else {}))
    mime = "image/jpeg" if image_format == "JPEG" else "image/png"
    return f"data:{mime};base64," + base64.b64encode(buffer.getvalue()).decode()


def is_qr_code(relative_path):
    # 二维码走无损 PNG，JPEG 压缩会让码点发糊、扫不出来
    return "二维码" in relative_path or "qr" in relative_path.lower()


def inline_images(slide_html, cache, image_root):
    def replace(match):
        relative_path = match.group(1).strip()
        if relative_path not in cache:
            source = image_root / relative_path
            if not source.exists():
                sys.exit(f"找不到图片：{source}")
            image_format = "PNG" if is_qr_code(relative_path) else "JPEG"
            cache[relative_path] = image_data_url(source, image_format=image_format)
        return cache[relative_path]
    return IMAGE_PATTERN.sub(replace, COMMENT_PATTERN.sub("", slide_html))


def mark_slide_source(slide_html, source_name):
    """给片段里每页 <section class="slide…"> 的起始标签末尾补 data-source；属性加在末尾，'<section class="slide' 计数不变。"""
    attribute = f' data-source="{html.escape(source_name)}"'
    return SLIDE_START_TAG.sub(lambda match: match.group(0)[:-1] + attribute + ">", slide_html)


class DiagramCollector(HTMLParser):
    """按出现顺序收集每个 .dg 的 (页码, [(属性名, 值), …])。页码按 class 含 slide 的 <section> 计；
    <script> 内容 HTMLParser 不解析，脚本生成的图元查不了（留给预览时的连线检查）。"""

    def __init__(self):
        super().__init__()
        self.page_number = 0
        self.diagrams = []
        self._open_tag = None
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = (attributes.get("class") or "").split()
        if tag == "section" and "slide" in classes:
            self.page_number += 1
        if self._open_tag is None:
            if "dg" in classes:
                self._open_tag, self._depth = tag, 1
                self.diagrams.append((self.page_number, []))
            return
        if tag == self._open_tag:
            self._depth += 1
        for name in ("data-id", "data-in", "data-from", "data-to"):
            if attributes.get(name) is not None:
                self.diagrams[-1][1].append((name[5:], attributes[name]))

    def handle_endtag(self, tag):
        if tag == self._open_tag:
            self._depth -= 1
            if self._depth == 0:
                self._open_tag = None


def diagram_reference_problems(slides_html):
    """返回 ["第 N 页 id：问题", …]，每条只报一次。每个 .dg 各查各的（和放映时一致）：
    id 在本图内不许重复，data-in 和连线端点（"节点:边" 去掉边再查）必须是本图里的 id。"""
    collector = DiagramCollector()
    collector.feed(slides_html)
    problems = {}
    for page_number, attributes in collector.diagrams:
        ids = [value for name, value in attributes if name == "id"]
        found = [f"第 {page_number} 页 {duplicate}：data-id 重复" for duplicate in dict.fromkeys(ids) if ids.count(duplicate) > 1]
        for name, value in attributes:
            target = value.split(":")[0]
            if name != "id" and target not in ids:
                found.append(f"第 {page_number} 页 {target}：{'data-in 指向的容器' if name == 'in' else '连线端点'}不存在")
        problems.update(dict.fromkeys(found))
    return list(problems)


def logo_markup(logo_path):
    if logo_path is None:
        return ""
    if not logo_path.exists():
        sys.exit(f"deck.json 里的 logo 不存在：{logo_path}")
    if logo_path.suffix.lower() == ".svg":
        source = logo_path.read_text(encoding="utf-8")
        lowered = source.lower()
        if "<script" in lowered or "javascript:" in lowered or re.search(r'(?:href|xlink:href)\s*=\s*["\'](?:https?:|//)', lowered):
            sys.exit("deck.json 里的 SVG logo 只能包含可信本地图形")
        encoded = base64.b64encode(source.encode("utf-8")).decode()
        return f'<img src="data:image/svg+xml;base64,{encoded}" alt="">'
    if logo_path.suffix.lower() == ".png":
        encoded = base64.b64encode(logo_path.read_bytes()).decode()
        return f'<img src="data:image/png;base64,{encoded}" alt="">'
    return f'<img src="{image_data_url(logo_path, 120, "PNG")}" alt="">'


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deck", type=Path, default=Path.cwd(), help="课件目录（含 deck.json、slides/、styles/）")
    parser.add_argument("--engine-root", type=Path, default=REPO, help="引擎根目录（含 styles/<风格>/manifest.json，清单路径相对它），默认仓库根")
    parser.add_argument("--only", nargs="*", default=[], help="只构建文件名以这些前缀开头的片段")
    parser.add_argument("--out", type=Path, default=None, help="输出路径，默认 deck.json 的 output")
    return parser.parse_args()


def load_style_manifest(engine_root, style_name):
    manifest_path = engine_root / "styles" / style_name / "manifest.json"
    if not manifest_path.exists():
        sys.exit(f"找不到风格清单：{manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    missing = [path for path in manifest["css"] + manifest["js"] + [manifest["backdrop"]] if not (engine_root / path).exists()]
    if missing:
        sys.exit(f"风格清单里的文件不存在：{missing}")
    return manifest


def build(deck_dir, engine_root, out_path, only):
    config = load_deck_config(deck_dir)
    manifest = load_style_manifest(engine_root, config["style"])
    # CSS 顺序：清单顺序在前，课件 styles/*.css 按文件名排序在后
    css_files = [engine_root / path for path in manifest["css"]] + sorted((deck_dir / "styles").glob("*.css"))
    css = "\n".join(path.read_text(encoding="utf-8") for path in css_files)
    js = "\n".join((engine_root / path).read_text(encoding="utf-8") for path in manifest["js"])
    backdrop = (engine_root / manifest["backdrop"]).read_text(encoding="utf-8").rstrip("\n")
    slide_files = sorted((deck_dir / "slides").glob("*.html"))
    if only:
        slide_files = [path for path in slide_files if path.name.startswith(tuple(only))]
    if not slide_files:
        sys.exit("slides/ 下没有匹配的片段")
    image_cache = {}
    slides_html = "\n".join(mark_slide_source(inline_images(path.read_text(encoding="utf-8"), image_cache, config["image_root"]), path.name)
                             for path in slide_files)
    reference_problems = diagram_reference_problems(slides_html)
    if reference_problems:
        sys.exit("连线检查没过：\n" + "\n".join(reference_problems))
    page = PAGE_SHELL.format(css=css, js=js, slides=slides_html, title=html.escape(config["title"]),
                             body_attrs=motion_body_attributes(config["motion"]),
                             brand=html.escape(config["brand"]), logo_img=logo_markup(config["logo"]), backdrop=backdrop)
    out_path = out_path or config["output"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    return {"slides": slides_html.count('<section class="slide'), "images": len(image_cache), "bytes": out_path.stat().st_size,
            "fragments": len(slide_files), "out": out_path}


def main():
    args = parse_args()
    summary = build(args.deck.resolve(), args.engine_root.resolve(), args.out, args.only)
    print(f"{summary['out']}: {summary['fragments']} 个片段, {summary['slides']} 页, {summary['images']} 张图, "
          f"{summary['bytes'] / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
