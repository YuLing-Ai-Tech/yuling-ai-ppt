// 放映内核 · 缩放、翻页（含分步揭示）、自动播放、定格、数字滚动、打字机、标题拆分、键盘与触屏
const stage = document.getElementById("stage");
const slides = [...document.querySelectorAll(".slide")];
const sectionLabel = document.getElementById("section-label");
const AUTOPLAY_MS = 9000;
const SETTLE_MS = 7000;
let current = 0;
let autoplayTimer = null;
let settleTimer = null;
const leavingTimers = new WeakMap();

function cancelLeaving(slide) {
  const timer = leavingTimers.get(slide);
  if (timer) clearTimeout(timer);
  leavingTimers.delete(slide);
  slide.classList.remove("leaving");
}

// 进场动画走完后定格，页面停在那里不再持续晃动
function scheduleSettle(slide) {
  clearTimeout(settleTimer);
  document.body.classList.remove("is-settled");
  slides.forEach(other => other.classList.remove("settled"));
  settleTimer = setTimeout(() => {
    slide.classList.add("settled");
    document.body.classList.add("is-settled");
  }, SETTLE_MS);
}

function fitStage() {
  const scale = Math.min(innerWidth / 1920, innerHeight / 1080);
  stage.style.transform = `translate(-50%, -50%) scale(${scale})`;
}

// 内容页的 h1/h2 按 <br> 拆行，每行包进遮罩，逐行升起
function splitHeadingLines() {
  document.querySelectorAll(".slide:not(.chapter) h1, .slide:not(.chapter) h2").forEach(heading => {
    if (heading.hasAttribute("data-a")) return;
    const lines = heading.innerHTML.split(/<br\s*\/?>/i);
    heading.innerHTML = lines.map((lineHtml, index) => `<span class="line"><span style="--l:${index}">${lineHtml}</span></span>`).join("");
  });
}


function countUp(slide) {
  slide.querySelectorAll("[data-count]").forEach(element => {
    const target = parseFloat(element.dataset.count);
    const decimals = (element.dataset.count.split(".")[1] || "").length;
    const suffix = element.dataset.suffix || "";
    const startAt = performance.now() + 500;
    const tick = now => {
      const progress = Math.min(Math.max((now - startAt) / 1600, 0), 1);
      const eased = 1 - Math.pow(1 - progress, 4);
      element.textContent = (target * eased).toFixed(decimals) + suffix;
      if (progress < 1 && slides[current] === slide) requestAnimationFrame(tick);
      else element.textContent = target.toFixed(decimals) + suffix;
    };
    requestAnimationFrame(tick);
  });
}

function typewrite(slide) {
  slide.querySelectorAll("[data-type]").forEach(element => {
    const fullText = element.dataset.type;
    const caret = '<span class="caret"></span>';
    let shown = 0;
    element.innerHTML = caret;
    const step = () => {
      if (slides[current] !== slide) { element.textContent = fullText; return; }
      shown += 1;
      element.innerHTML = fullText.slice(0, shown).replace(/\n/g, "<br>") + caret;
      if (shown < fullText.length) setTimeout(step, 70);
    };
    setTimeout(step, 700);
  });
}

// revealAll：本页的 data-step 是否直接全部揭示；只有 advance() 顺序翻页时传 false（见 runtime/steps.js）
function show(index, revealAll = true) {
  const next = Math.max(0, Math.min(slides.length - 1, index));
  const previous = slides[current];
  const slide = slides[next];
  // 快速往返时，目标页可能仍在上一轮 800ms 离场窗口里；先取消旧状态，避免
  // .slide.leaving（声明在 .slide.active 之后）把已激活页面继续压成透明。
  cancelLeaving(slide);
  if (next !== current) {
    previous.classList.remove("active");
    previous.classList.add("leaving");
    const timer = setTimeout(() => {
      if (!previous.classList.contains("active")) previous.classList.remove("leaving");
      leavingTimers.delete(previous);
    }, 800);
    leavingTimers.set(previous, timer);
  }
  current = next;
  slide.classList.add("active");
  enterSteps(slide, revealAll);
  (window.componentEnterSteps || []).forEach(step => step(slide, previous));
  (window.styleEnterSteps || []).forEach(step => step(slide, previous));
  document.body.classList.toggle("is-night", slide.classList.contains("chapter"));
  countUp(slide);
  typewrite(slide);
  scheduleSettle(slide);
  sectionLabel.textContent = slide.dataset.section || "";
  document.querySelector("#bar i").style.width = `${(current + 1) / slides.length * 100}%`;
  document.getElementById("pageno").textContent = `${current + 1} / ${slides.length}`;
  history.replaceState(null, "", `#${current + 1}`);
}

// 下一步：本页还有没揭示的步骤就先揭示一步，揭示完才翻页
function advance() {
  if (revealNextStep(slides[current])) return;
  if (current < slides.length - 1) show(current + 1, false);
}

// 上一步：本页揭示过步骤就先收回一步，否则回到上一页（上一页全部揭示）
function retreat() {
  if (hideLastStep(slides[current])) return;
  show(current - 1);
}

function toggleAutoplay() {
  const button = document.getElementById("play");
  if (autoplayTimer) {
    clearInterval(autoplayTimer);
    autoplayTimer = null;
    button.textContent = "播放";
    button.classList.remove("is-on");
    return;
  }
  autoplayTimer = setInterval(() => {
    if (current >= slides.length - 1 && !hasHiddenStep(slides[current])) toggleAutoplay();
    else advance();
  }, AUTOPLAY_MS);
  button.textContent = "暂停";
  button.classList.add("is-on");
}

document.addEventListener("keydown", event => {
  if (["ArrowRight", "ArrowDown", "PageDown", " ", "Enter"].includes(event.key)) advance();
  else if (["ArrowLeft", "ArrowUp", "PageUp", "Backspace"].includes(event.key)) retreat();
  else if (event.key === "Home") show(0);
  else if (event.key === "End") show(slides.length - 1);
  else if (event.key.toLowerCase() === "p" && !event.metaKey && !event.ctrlKey && !event.altKey) toggleAutoplay();
  else if (event.key.toLowerCase() === "s" && !event.metaKey && !event.ctrlKey && !event.altKey) document.body.classList.toggle("flow-paused");
  else if (event.key.toLowerCase() === "f" && !event.metaKey && !event.ctrlKey && !event.altKey) document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();
});

let touchStartX = null;
addEventListener("touchstart", event => { touchStartX = event.touches[0].clientX; });
addEventListener("touchend", event => {
  if (touchStartX === null) return;
  const dx = event.changedTouches[0].clientX - touchStartX;
  if (Math.abs(dx) > 50) dx < 0 ? advance() : retreat();
  touchStartX = null;
});

document.getElementById("prev").addEventListener("click", retreat);
document.getElementById("next").addEventListener("click", advance);
document.getElementById("play").addEventListener("click", toggleAutoplay);
addEventListener("resize", fitStage);
setTimeout(() => { document.getElementById("hint").style.opacity = 0; }, 5000);
