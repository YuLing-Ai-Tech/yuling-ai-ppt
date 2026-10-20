// 通用组件 · 点击揭示答案（Q-017 D6）：点没揭示的 .answer，本页的分步揭示直接走到它那一步（它之前的步骤一起揭示）；
// 按 → 照常一步一步揭示。setShownStep、stepNumbers 在 runtime/steps.js，scheduleSettle 在 runtime/deck.js
function revealAnswerOnClick(event) {
  const answer = event.target.closest(".slide.active .answer[data-step]:not(.step-shown)");
  if (!answer) return;
  const slide = answer.closest(".slide");
  setShownStep(slide, stepNumbers(slide).indexOf(Number(answer.dataset.step) || 0) + 1, false);
  scheduleSettle(slide);
}

document.addEventListener("click", revealAnswerOnClick);
