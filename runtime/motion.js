// 受控动效运行时：只负责暂停/恢复和向 QA 暴露可审计配置。
function syncMotionVisibility() {
  document.body.classList.toggle("motion-hidden", document.hidden);
}

document.addEventListener("visibilitychange", syncMotionVisibility);
syncMotionVisibility();

window.motionPlanRuntime = Object.freeze({
  persona: document.body.dataset.motionPersona || "",
  recipe: document.body.dataset.motionRecipe || "",
  background: document.body.dataset.motionBackground || "",
  transition: document.body.dataset.motionTransition || "",
  fingerprint: document.body.dataset.motionFingerprint || "",
});
