// 苹果风 · 卡片鼠标高光与 3D 倾斜
// 卡片、窗口：鼠标高光跟随 + 3D 倾斜
function attachPointerLight() {
  document.querySelectorAll(".glass, .win").forEach(card => {
    card.addEventListener("pointermove", event => {
      const rect = card.getBoundingClientRect();
      const x = (event.clientX - rect.left) / rect.width, y = (event.clientY - rect.top) / rect.height;
      card.style.setProperty("--mx", `${x * 100}%`);
      card.style.setProperty("--my", `${y * 100}%`);
      card.style.setProperty("--ry", `${(x - .5) * 10}deg`);
      card.style.setProperty("--rx", `${(.5 - y) * 8}deg`);
      card.classList.add("is-hover");
    });
    card.addEventListener("pointerleave", () => {
      card.classList.remove("is-hover");
      card.style.setProperty("--rx", "0deg");
      card.style.setProperty("--ry", "0deg");
    });
  });
  const nightsky = document.getElementById("nightsky");
  stage.addEventListener("pointermove", event => {
    const rect = stage.getBoundingClientRect();
    nightsky.style.setProperty("--sx", `${(event.clientX - rect.left) / rect.width * 100}%`);
    nightsky.style.setProperty("--sy", `${(event.clientY - rect.top) / rect.height * 100}%`);
  });
}
(window.styleBootSteps = window.styleBootSteps || []).push(attachPointerLight);
