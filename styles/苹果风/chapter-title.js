// 苹果风 · 章节页大标题拆成单字（配合 chapter.css 的 ch-in 逐字翻入）
function splitChapterTitles() {
  document.querySelectorAll(".chapter h1[data-split]").forEach(title => {
    let charIndex = 0;
    const wrapText = node => {
      [...node.childNodes].forEach(child => {
        if (child.nodeType === Node.TEXT_NODE) {
          const fragment = document.createDocumentFragment();
          [...child.textContent].forEach(character => {
            const span = document.createElement("span");
            span.className = "ch";
            span.style.setProperty("--c", charIndex++);
            span.textContent = character === " " ? " " : character;
            fragment.appendChild(span);
          });
          child.replaceWith(fragment);
        } else if (child.nodeType === Node.ELEMENT_NODE && child.tagName !== "BR") {
          wrapText(child);
        }
      });
    };
    wrapText(title);
  });
}
(window.styleBootSteps = window.styleBootSteps || []).push(splitChapterTitles);
