// 放映内核 · 分步揭示（设计 §3.2）：data-step="N" 的元素按 N 依次出现。
// 按 → 顺序进来的页从第 0 步开始，每按一次揭示一步，揭示完才翻页；其余方式进页（地址栏 #N、页面地图、Home/End、←）直接全部揭示
const STEP_STAGGER_MAX_S = 0.9;
const STEP_STAGGER_SPAN_S = 4.2;  // 一次揭示全部时，最后一步在 4.2 秒内开始，登场动画 6 秒内做完
const shownSteps = new Map();

// 步号只决定先后，不要求连续：按页上实际出现的步号（去重、从小到大）逐个揭示
function stepNumbers(slide) {
  const numbers = [...slide.querySelectorAll("[data-step]")].map(element => Number(element.dataset.step) || 0);
  return [...new Set(numbers)].sort((first, second) => first - second);
}

function stepCount(slide) {
  return stepNumbers(slide).length;
}

// 一次揭示全部时相邻两步的间隔（秒）
function stepStagger(total) {
  return total > 1 ? Math.min(STEP_STAGGER_MAX_S, STEP_STAGGER_SPAN_S / (total - 1)) : 0;
}

// target：已揭示的步数（第几个不同的步号）；同步号的元素一起出现
function setShownStep(slide, target, staggered) {
  const numbers = stepNumbers(slide);
  const stagger = staggered ? stepStagger(numbers.length) : 0;
  slide.querySelectorAll("[data-step]").forEach(element => {
    const rank = numbers.indexOf(Number(element.dataset.step) || 0) + 1;
    const visible = rank <= target;
    if (visible && !element.classList.contains("step-shown")) element.style.setProperty("--step-delay", `${(rank - 1) * stagger}s`);
    element.classList.toggle("step-shown", visible);
  });
  shownSteps.set(slide, target);
}

function enterSteps(slide, revealAll) {
  const total = stepCount(slide);
  if (!total) return;
  slide.querySelectorAll(".step-shown").forEach(element => element.classList.remove("step-shown"));
  setShownStep(slide, revealAll ? total : 0, revealAll);
}

function hasHiddenStep(slide) {
  return (shownSteps.get(slide) ?? stepCount(slide)) < stepCount(slide);
}

// 本页还有没揭示的步骤就揭示下一步，返回 true；没有返回 false
function revealNextStep(slide) {
  if (!hasHiddenStep(slide)) return false;
  setShownStep(slide, shownSteps.get(slide) + 1, false);
  scheduleSettle(slide);
  return true;
}

// 本页已揭示过步骤就收回最后一步，返回 true；已在第 0 步或没有步骤返回 false
function hideLastStep(slide) {
  const shown = shownSteps.get(slide) || 0;
  if (!stepCount(slide) || shown <= 0) return false;
  setShownStep(slide, shown - 1, false);
  return true;
}
