// 苹果风 · 进页效果：进深色章节页时横扫光幕；夜空极光跟随当前页主题配色
function runChapterWipe(slide, previous) {
  if (!slide.classList.contains("chapter") || previous === slide) return;
  const wipe = document.getElementById("wipe");
  wipe.classList.remove("run");
  void wipe.offsetWidth;
  wipe.classList.add("run");
}

function tintNightSky(slide) {
  const nightsky = document.getElementById("nightsky");
  ["--c1", "--c2", "--c3"].forEach(name => nightsky.style.setProperty(name, getComputedStyle(slide).getPropertyValue(name)));
}

(window.styleEnterSteps = window.styleEnterSteps || []).push(runChapterWipe, tintNightSky);
