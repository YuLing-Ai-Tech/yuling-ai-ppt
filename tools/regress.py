"""苹果风原版回归：确定性逐页截图，和甬舟 94 页基准逐像素比对，证明"改过的引擎 = 原版效果"。

Public 图元样板：engine 检查使用 platforms/<系统>-x64 的获批目标，先核验环境。
根目录图片为历史档案，不再由 baseline 子命令覆盖；新目标必须先审查候选原图。

用法：
  python3 tools/regress.py engine [--engine-root 目录] [--work 目录] [--suite 甬舟94|图元样板]
      改过引擎就跑这个：默认（--suite 甬舟94）用 风格清单 + examples/甬舟94 构建 94 页，截图后和 baselines/甬舟94 基准比对；
      --suite 图元样板 则用 examples/图元样板 构建 9 页，和 baselines/图元样板 比对。
  python3 tools/regress.py baseline <课件.html> [--suite 甬舟94|图元样板]
      重做基准（默认写入 baselines/甬舟94，--suite 图元样板 写入 baselines/图元样板；并重生成 manifest.json）。只在确认"新效果就是想要的"或 Chrome 升级后才做。
      基准要用"最近一次验收提交"的构建来截（git worktree 检出那个提交再 build_deck），截完再用 HEAD 跑 engine 比对。
  python3 tools/regress.py shoot <课件.html> <截图目录>
  python3 tools/regress.py compare <基准目录> <截图目录> <差异图目录>
退出码：0 = 每页 0 差异（engine 子命令为首拍或重拍后 0 差异）；1 = 有差异页、JS 报错或页数不符。

确定性模式（不改引擎源码，只改临时副本和浏览器环境）：
  - 在 <head> 最前面插入：固定种子的 Math.random（粒子位置）、按调用时刻计时的 rAF + 冻结样式
    （animation-delay:-60s; animation-play-state:paused; transition:none）。
    必须随页面一起加载；页面打开后再注入的话，动画已按真实时间跑了一段，两次截图对不上。
    循环动画（极光、渐变字）因此停在同一相位，登场动画停在结束帧。
  - playwright 假时钟：加载前暂停，加载后拨快 10 秒。打字机、数字滚动、7 秒定格都走引擎自己的逻辑到终态，
    粒子也固定跑同样多帧。
  - 每页单独打开 <课件>#N，互不影响。临时副本放在系统临时目录，所以课件须是 build_deck.py 产出的单文件（图片已内嵌）。
  - engine 子命令里首拍有差异的页，会逐页串行单独重拍一次再比；重拍仍有差异才报红，首拍差异图留在差异图目录
    （假时钟每走一个计时器就让出一次真实时间，真实帧落在哪个假时刻随负载变；2026-09-30 实测 P69 圆点偶发差 1 像素）。
    阈值仍是 0 像素，基准不变（赵老师 2026-09-30 拍板）。
  图元样板基准（baselines/图元样板）同样的阈值和重拍语义；不许为了变绿重做，规则见 docs/计划-M3-图元-2026-09-30.md「图元样板基准规则」。
盲区：只比最终画面。只播一次的登场动画改缓动、时长而结束状态不变，这里抓不到；循环动画改缓动会因相位变化被抓到
（2026-09-29 实测：--ease 改成 linear，只有用它做循环动画的 6 页报红，其余 88 页 0 差异）。
"""

import argparse
import asyncio
import datetime
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops
from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))
from tools.build_deck import build  # noqa: E402
from tools.visual_environment import environment_snapshot, platform_baseline, require_environment, reserve_candidate_directory  # noqa: E402

EXAMPLE_DECK_DIR = REPO / "examples/甬舟94"
BASELINE_DIR = REPO / "baselines/甬舟94"
# 回归套件：名字 → (样张目录, 基准目录)。两套基准各管各的，重做一套不碰另一套
SUITES = {"甬舟94": (EXAMPLE_DECK_DIR, BASELINE_DIR), "图元样板": (REPO / "examples/图元样板", REPO / "baselines/图元样板")}
MANIFEST_NAME = "manifest.json"
# 阈值 0（赵老师 2026-09-29 拍板）：原版 94 页连截两次实测每页 0 差异，没有需要容忍的噪声。
# Chrome 升级导致的差异是成片的，小阈值也盖不住，靠 meta.json 里的版本号提示后重做基准。
ALLOWED_DIFF_PIXELS = 0
VIEWPORT = {"width": 1920, "height": 1080}
CLOCK_START_MS = 1_790_000_000_000
SETTLE_RUN_MS = 10_000
PARALLEL_PAGES = 4
# 软件绘制，排除 GPU 这个变量（稳定性由下面的 rAF 处理解决；GPU 模式单页 24 次也一致，全量未验）
CHROME_ARGS = ["--disable-gpu", "--force-color-profile=srgb", "--disable-lcd-text", "--disable-partial-raster"]


def browser_launch_kwargs(args=None):
    """Use a pinned browser for visual QA without replacing the user's Chrome."""
    options = {"headless": True}
    chrome_path = os.environ.get("PPT_CHROME_PATH")
    if chrome_path:
        options["executable_path"] = chrome_path
    else:
        options["channel"] = "chrome"
    if args is not None:
        options["args"] = args
    return options

# 固定种子的 Math.random（粒子初始位置）。requestAnimationFrame 改成假时钟上"16ms 后"的 setTimeout：
# 假时钟的 rAF 按时钟原点对齐，而每页 performance.now() 起点不固定（实测 2～70ms），
# 粒子帧和 7 秒定格计时器的相位就会差半帧，定格前多跑或少跑一帧（实测 437 / 438 帧），粒子页每次不同
DETERMINISM_JS = """(() => { let seed = 20260927;
  Math.random = () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  window.requestAnimationFrame = callback => setTimeout(() => callback(performance.now()), 16);
  window.cancelAnimationFrame = clearTimeout; })();"""
# 选择器带三个 :not(#…) 抬高优先级：P62 练习秒表的豁免规则（.slide.settled .e03-watch b { running !important }）
# 比 * 优先级高，不压住它，秒表会按真实时间继续走，两次截图差 1 秒
FREEZE_SELECTOR = "*:not(#r-1):not(#r-2):not(#r-3)"
FREEZE_CSS = (f"{FREEZE_SELECTOR}, {FREEZE_SELECTOR}::before, {FREEZE_SELECTOR}::after {{ animation-delay: -60s !important; animation-play-state: paused !important; "
              "transition: none !important; }")


def write_frozen_copy(deck_path, target_dir):
    source = deck_path.read_text()
    if source.count("<head>") != 1:
        sys.exit(f"{deck_path} 里 <head> 不是恰好一个，无法插入确定性脚本")
    injected = f"<head>\n<script>{DETERMINISM_JS}</script>\n<style>{FREEZE_CSS}</style>"
    frozen_path = target_dir / "frozen.html"
    frozen_path.write_text(source.replace("<head>", injected, 1))
    return frozen_path


async def shoot_page(browser, deck_uri, page_number, shot_dir, errors, geometry=None):
    page = await browser.new_page(viewport=VIEWPORT)
    page.on("pageerror", lambda error: errors.append(f"第 {page_number} 页：{error}"))
    await page.clock.install(time=CLOCK_START_MS)
    await page.clock.pause_at(CLOCK_START_MS + 1000)
    await page.goto(f"{deck_uri}#{page_number}")
    await page.clock.run_for(SETTLE_RUN_MS)
    await page.screenshot(path=str(shot_dir / f"p{page_number:02d}.png"))
    if geometry is not None:
        geometry[page_number] = await page.evaluate("""() => [...document.querySelectorAll('.slide.active [data-at]')].map(node => {
            const rect = node.getBoundingClientRect();
            return {at: node.dataset.at, x: rect.x, y: rect.y, width: rect.width, height: rect.height};
        })""")
    await page.close()


async def shoot_deck(deck_path, shot_dir, expected_environment=None, record_environment=False):
    """逐页确定性截图，返回 (页数, JS 报错列表, 浏览器版本)。"""
    shot_dir.mkdir(parents=True, exist_ok=True)
    for old_shot in shot_dir.glob("p*.png"):
        old_shot.unlink()
    errors = []
    geometry = {} if record_environment else None
    environment = None
    with tempfile.TemporaryDirectory(prefix="regress_frozen_") as frozen_dir:
        deck_uri = write_frozen_copy(deck_path, Path(frozen_dir)).as_uri()
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(**browser_launch_kwargs(CHROME_ARGS))
            if record_environment:
                environment = environment_snapshot(os.environ.get("PPT_CHROME_PATH"), browser.version, CHROME_ARGS, VIEWPORT)
                if environment["chromeVersion"] != "152.0.7977.64" or environment["playwrightVersion"] != "1.60.0":
                    await browser.close()
                    raise ValueError("Candidate requires Chrome 152.0.7977.64 and Playwright 1.60.0")
            if expected_environment is not None:
                require_environment(expected_environment, environment_snapshot(
                    os.environ.get("PPT_CHROME_PATH"), browser.version, CHROME_ARGS, VIEWPORT))
            counter = await browser.new_page()
            await counter.goto(deck_uri)
            total = await counter.evaluate("document.querySelectorAll('.slide').length")
            await counter.close()
            limiter = asyncio.Semaphore(PARALLEL_PAGES)

            async def limited(page_number):
                async with limiter:
                    await shoot_page(browser, deck_uri, page_number, shot_dir, errors, geometry)

            await asyncio.gather(*(limited(number) for number in range(1, total + 1)))
            browser_version = browser.version
            await browser.close()
    write_meta(shot_dir, deck_path, total, browser_version)
    if record_environment:
        (shot_dir / "environment.json").write_text(json.dumps(environment, indent=2) + "\n", encoding="utf-8")
        (shot_dir / "geometry.json").write_text(json.dumps(geometry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return total, errors, browser_version


def write_meta(shot_dir, deck_path, total, browser_version):
    beijing_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    meta = {"deck": str(deck_path.resolve()), "pages": total, "chrome": browser_version,
            "playwright": importlib.metadata.version("playwright"), "shot_at_beijing": beijing_now.strftime("%Y-%m-%d %H:%M")}
    (shot_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")


def count_diff_pixels(baseline_image, candidate_image):
    """返回 (差异像素数, 差异掩码)。任一通道差 ≥1 就算差异；不能先转灰度，那样单通道 1 级的差会被四舍五入成 0。"""
    red, green, blue = ImageChops.difference(baseline_image, candidate_image).split()
    channel_max = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    mask = channel_max.point(lambda value: 255 if value else 0)
    return mask.histogram()[255], mask


def save_diff_image(baseline_image, mask, diff_path):
    # 基准图压暗做底，差异像素涂成纯红，一眼看出差在哪
    dimmed = baseline_image.convert("L").point(lambda value: value // 3).convert("RGB")
    dimmed.paste((255, 0, 0), mask=mask)
    dimmed.save(diff_path)


def compare_shots(baseline_dir, shot_dir, diff_dir):
    """逐页比对，打印每页差异像素数，返回是否全部通过。"""
    baseline_names = sorted(path.name for path in baseline_dir.glob("p*.png"))
    shot_names = sorted(path.name for path in shot_dir.glob("p*.png"))
    if not baseline_names:
        print(f"基准目录没有截图：{baseline_dir}")
        return False, []
    if baseline_names != shot_names:
        print(f"页数不符：基准 {len(baseline_names)} 页，本次 {len(shot_names)} 页")
        return False, []
    warn_version_change(baseline_dir, shot_dir)
    diff_dir.mkdir(parents=True, exist_ok=True)
    failed_pages = []
    for name in baseline_names:
        baseline_image = Image.open(baseline_dir / name).convert("RGB")
        candidate_image = Image.open(shot_dir / name).convert("RGB")
        if baseline_image.size != candidate_image.size:
            print(f"{name}: 尺寸不符 {baseline_image.size} vs {candidate_image.size}")
            failed_pages.append(name)
            continue
        diff_pixels, mask = count_diff_pixels(baseline_image, candidate_image)
        print(f"{name}: {diff_pixels} 像素不同")
        if diff_pixels > ALLOWED_DIFF_PIXELS:
            failed_pages.append(name)
            save_diff_image(baseline_image, mask, diff_dir / name.replace("p", "d", 1))
    page_numbers = [int(name[1:3]) for name in failed_pages]
    verdict = "通过" if not failed_pages else f"报红，差异页：{page_numbers}，差异图在 {diff_dir}"
    print(f"共 {len(baseline_names)} 页，阈值 {ALLOWED_DIFF_PIXELS} 像素；{verdict}")
    return not failed_pages, page_numbers


def warn_version_change(baseline_dir, shot_dir):
    try:
        meta_path = baseline_dir / "meta.json"
        if meta_path.exists():
            baseline_meta = json.loads(meta_path.read_text(encoding="utf-8"))
        else:
            environment = json.loads((baseline_dir / MANIFEST_NAME).read_text(encoding="utf-8"))["environment"]
            baseline_meta = {"chrome": environment["chromeVersion"], "playwright": environment["playwrightVersion"]}
        shot_meta = json.loads((shot_dir / "meta.json").read_text())
    except (OSError, KeyError, json.JSONDecodeError):
        print("提示：缺少 meta.json，无法核对浏览器版本")
        return
    for key in ("chrome", "playwright"):
        if baseline_meta.get(key) != shot_meta.get(key):
            print(f"提示：{key} 版本变了（基准 {baseline_meta.get(key)} → 本次 {shot_meta.get(key)}），"
                  "成片差异可能来自浏览器；确认引擎没动过再用 baseline 重做基准")


def build_example_deck(engine_root, build_dir, deck_dir=EXAMPLE_DECK_DIR):
    build_dir.mkdir(parents=True, exist_ok=True)
    return build(Path(deck_dir).resolve(), Path(engine_root).resolve(), build_dir / "regress.html", [])["out"]


def shoot(deck_path, shot_dir, expected_environment=None):
    total, errors, browser_version = asyncio.run(shoot_deck(Path(deck_path), Path(shot_dir), expected_environment))
    print(f"截图 {total} 页（Chrome {browser_version}）；JS 报错：{errors or '无'}")
    return not errors


def png_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_baseline_manifest(baseline_dir):
    digests = {path.name: png_digest(path) for path in sorted(baseline_dir.glob("p*.png"))}
    meta = json.loads((baseline_dir / "meta.json").read_text())
    manifest = {"chrome": meta["chrome"], "playwright": meta["playwright"], "pages": len(digests), "sha256": digests}
    (baseline_dir / MANIFEST_NAME).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def rebaseline(deck_path, baseline_dir):
    """重做基准：截图有 JS 报错就不改清单，避免把坏截图登记成基准（清单和 PNG 对不上，下次比对会直接报红）。"""
    if not shoot(deck_path, baseline_dir):
        print(f"截图有 JS 报错，清单未更新：{baseline_dir / MANIFEST_NAME}")
        return False
    write_baseline_manifest(baseline_dir)
    print(f"基准已写入：{baseline_dir}")
    return True


def verify_baseline_manifest(baseline_dir):
    """比对前核对基准 PNG 和已提交清单一致，防止拿错基准比出假绿。"""
    manifest = json.loads((baseline_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    mismatched = [name for name, digest in manifest["sha256"].items()
                  if not (baseline_dir / name).exists() or png_digest(baseline_dir / name) != digest]
    return sorted(mismatched)


def run_engine_check(engine_root, work_dir, deck_dir=None, baseline_dir=None):
    """deck_dir 和 baseline_dir 要么一起给（某个套件），要么都不给（甬舟 94）；只给一个会拿错基准比对，直接报错。"""
    if (deck_dir is None) != (baseline_dir is None):
        raise ValueError("deck_dir 和 baseline_dir 必须同时给出，或都不给（默认甬舟94）")
    if deck_dir is None:
        deck_dir, baseline_dir = EXAMPLE_DECK_DIR, BASELINE_DIR
    mismatched = verify_baseline_manifest(baseline_dir)
    if mismatched:
        print(f"基准截图和清单不一致：{mismatched}；先用 baseline 子命令重做或找回正确基准")
        return False, []
    manifest = json.loads((baseline_dir / MANIFEST_NAME).read_text(encoding="utf-8"))
    expected_environment = manifest.get("environment")
    if Path(baseline_dir).parent.name == "platforms" and expected_environment is None:
        raise ValueError("Platform baseline environment missing")
    deck_path = build_example_deck(engine_root, work_dir / "build", deck_dir)
    shots_ok = shoot(deck_path, work_dir / "shots", expected_environment)
    compare_ok, failed_pages = compare_shots(baseline_dir, work_dir / "shots", work_dir / "diffs")
    if failed_pages:
        print(f"首拍差异页 {failed_pages}，逐页单独重拍一次再比；首拍差异图改名为 d<页号>-首拍.png 保留")
        keep_first_shot_diffs(work_dir / "diffs", failed_pages)
        retake_errors = asyncio.run(retake_pages(deck_path, work_dir / "shots", failed_pages))
        print(f"重拍 JS 报错：{retake_errors or '无'}")
        shots_ok = shots_ok and not retake_errors
        compare_ok, failed_pages = compare_shots(baseline_dir, work_dir / "shots", work_dir / "diffs")
    return shots_ok and compare_ok, failed_pages


def keep_first_shot_diffs(diff_dir, page_numbers):
    """首拍差异图改名保留，重拍仍红时新差异图不会把它覆盖。"""
    for page_number in page_numbers:
        (diff_dir / f"d{page_number:02d}.png").replace(diff_dir / f"d{page_number:02d}-首拍.png")


async def retake_pages(deck_path, shot_dir, page_numbers):
    """逐页串行重拍（不并发，少受负载影响），覆盖原截图，返回 JS 报错列表。"""
    errors = []
    with tempfile.TemporaryDirectory(prefix="regress_frozen_") as frozen_dir:
        deck_uri = write_frozen_copy(Path(deck_path), Path(frozen_dir)).as_uri()
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(**browser_launch_kwargs(CHROME_ARGS))
            for page_number in page_numbers:
                await shoot_page(browser, deck_uri, page_number, shot_dir, errors)
            await browser.close()
    return errors


def parse_args():
    parser = argparse.ArgumentParser(description="苹果风原版回归：确定性截图 + 逐像素比对")
    commands = parser.add_subparsers(dest="command", required=True)
    candidate = commands.add_parser("candidate", help="Capture two independent candidate runs outside repositories; never adopt a baseline")
    candidate.add_argument("--suite", choices=["图元样板"], required=True)
    candidate.add_argument("--work", type=Path, required=True)
    engine = commands.add_parser("engine", help="用引擎 + examples/甬舟94 构建 94 页并和基准比对")
    engine.add_argument("--engine-root", type=Path, default=REPO, help="引擎根目录（含 styles/<风格>/manifest.json），默认仓库根")
    engine.add_argument("--work", type=Path, default=None, help="构建、截图、差异图放哪，默认新建临时目录")
    engine.add_argument("--suite", choices=sorted(SUITES), default="甬舟94", help="比哪套样张和基准，默认甬舟94")
    baseline = commands.add_parser("baseline", help="重做一套基准截图（写入 baselines/<套件>）")
    baseline.add_argument("deck", type=Path)
    baseline.add_argument("--suite", choices=sorted(SUITES), default="甬舟94", help="写哪套基准，默认甬舟94")
    shoot = commands.add_parser("shoot", help="任意课件逐页确定性截图")
    shoot.add_argument("deck", type=Path)
    shoot.add_argument("shot_dir", type=Path)
    compare = commands.add_parser("compare", help="两组截图逐页比对")
    compare.add_argument("baseline_dir", type=Path)
    compare.add_argument("shot_dir", type=Path)
    compare.add_argument("diff_dir", type=Path)
    return parser.parse_args()


def capture_candidate(work):
    work = reserve_candidate_directory(work)
    source = {
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO).decode().strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO)),
    }
    report = {"status": "incomplete", "source": source, "pythonVersion": sys.version.split()[0],
              "pillowVersion": importlib.metadata.version("pillow"), "approved": False}
    report_path = work / "candidate.json"
    try:
        if source["dirty"]:
            raise ValueError("Candidate capture requires a clean source commit")
        deck = build_example_deck(REPO, work / "build", SUITES["图元样板"][0])
        for name in ("candidate-a", "candidate-b"):
            total, errors, _ = asyncio.run(shoot_deck(deck, work / name, record_environment=True))
            if total != 9 or errors:
                raise ValueError(f"Candidate capture failed: {total} pages, {len(errors)} JS errors")
        env_a = json.loads((work / "candidate-a/environment.json").read_text())
        env_b = json.loads((work / "candidate-b/environment.json").read_text())
        require_environment(env_a, env_b)
        report["environment"] = env_a
        passed, pages = compare_shots(work / "candidate-a", work / "candidate-b", work / "diffs")
        report["differentPages"] = pages
        report["sha256"] = {p.name: png_digest(p) for p in sorted((work / "candidate-a").glob("p*.png"))}
        hashes_equal = all(png_digest(work / "candidate-b" / name) == digest for name, digest in report["sha256"].items())
        if not passed or not hashes_equal:
            raise ValueError("Independent candidate captures differ; evidence retained")
        if subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO) or source["commit"] != subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO).decode().strip():
            raise ValueError("Source changed during candidate capture")
        report["status"] = "repeatable; owner review required"
        return True
    except Exception as error:
        report["failure"] = str(error)
        raise
    finally:
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main():
    args = parse_args()
    if args.command == "candidate":
        passed = capture_candidate(args.work)
    elif args.command == "engine":
        work_dir = args.work or Path(tempfile.mkdtemp(prefix="regress_engine_"))
        print(f"工作目录：{work_dir}")
        deck_dir, baseline_dir = SUITES[args.suite]
        if args.suite == "图元样板":
            baseline_dir = platform_baseline(baseline_dir)
        passed, _ = run_engine_check(args.engine_root, work_dir, deck_dir, baseline_dir)
    elif args.command == "baseline":
        if args.suite == "图元样板":
            raise SystemExit("Platform baselines require reviewed candidate images; automatic re-recording is disabled")
        passed = rebaseline(args.deck, SUITES[args.suite][1])
    elif args.command == "shoot":
        passed = shoot(args.deck, args.shot_dir)
    else:
        passed, _ = compare_shots(args.baseline_dir, args.shot_dir, args.diff_dir)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
