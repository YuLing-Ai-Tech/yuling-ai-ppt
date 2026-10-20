// 图元 · 原子装饰（设计 §4.4）：图例按连线类型生成条目，时间轴按 data-ticks 均分刻度，象限坐标写上两条轴的名字
const DIAGRAM_KIND_NAMES = { sync: "同步调用", async: "异步事件", data: "数据读写", human: "人工介入", tele: "遥测" };

// data-kinds="sync data:写库"：冒号后是自定义名字，不写用默认名
function decorateLegend(legend) {
  legend.dataset.kinds.trim().split(/\s+/).forEach(entry => {
    const [kind, name] = entry.split(":");
    const item = document.createElement("span");
    item.dataset.kind = kind;
    item.append(document.createElement("i"), name || DIAGRAM_KIND_NAMES[kind] || kind);
    legend.append(item);
  });
}

// data-ticks="2025 Q1|2025 Q2|…"：首尾刻度贴两端，中间均分
function decorateAxis(axis) {
  const ticks = axis.dataset.ticks.split("|").map(text => text.trim());
  ticks.forEach((text, index) => {
    const tick = document.createElement("span");
    tick.className = "tick";
    tick.style.left = `${ticks.length > 1 ? index / (ticks.length - 1) * 100 : 0}%`;
    tick.textContent = text;
    axis.append(tick);
  });
}

function decorateQuadrant(quadrant) {
  [["x", quadrant.dataset.x], ["y", quadrant.dataset.y]].filter(([, text]) => text).forEach(([axisName, text]) => {
    const title = document.createElement("span");
    title.className = `axis-title axis-${axisName}`;
    title.textContent = text;
    quadrant.append(title);
  });
}

function decorateAtoms(boxes) {
  boxes.forEach(({ element }) => {
    if (element.matches(".legend[data-kinds]")) decorateLegend(element);
    else if (element.matches(".axis[data-ticks]")) decorateAxis(element);
    else if (element.matches(".quadrant")) decorateQuadrant(element);
  });
}
