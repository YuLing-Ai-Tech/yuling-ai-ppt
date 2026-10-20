// 图元 · 放映时拖动（Q-017 D2 形态 A，存回见下方形态 B）：默认关闭；按 DRAG_TOGGLE_KEY 或点"拖动"按钮打开。拖节点或容器，线跟着重画；刷新复原。
// Pointer Events 一套代码管鼠标和触摸屏。按下后移动不到 DRAG_THRESHOLD_PX 算点选（照常交给聚焦）；拖过了就吞掉随后那次 click。
// 拖动模式下暂停触摸滑动翻页；没揭示的分步元素不能拖。坐标吸附到 1 / DRAG_SNAP 格
const DRAG_TOGGLE_KEY = "t";      // 暂定，检查点 C 定
const DRAG_THRESHOLD_PX = 6;      // 屏幕像素
const DRAG_SNAP = 10;             // 每格分 10 份，即吸附到 0.1 格
const DRAG_BUTTON_IDLE_MS = 3000; // 指针停下这么久后按钮淡出（拖动模式开着时一直显示）
let dragState = null;  // { part, dg, pointerId, startX, startY, at, cell, moved }
let dragSwallowClick = false;
let dragIdleTimer = null;
// 形态 B：拖过的盒子记下来，"保存位置"写成位置文件，tools/apply_positions.py 按它写回 slides/*.html
const DRAG_POSITIONS_FORMAT = "yuling-positions-1";  // 改格式要同步改 tools/apply_positions.py
const dragMoves = new Map();  // "来源文件|第几个 .dg|id" → { page, source, diagram, id, at, was }
// was：该节点源文件里 data-at 的原值。脚本一加载就记（树图、循环图排版在启动时才补 data-at，那时再读就不是源里的值了）；源里没写的记 ""
const dragSourceAt = new Map([...document.querySelectorAll(".slide .dg [data-id]")].map(element => [element, element.getAttribute("data-at") || ""]));

const isDragOn = () => document.body.classList.contains("drag-on");
const snapToGrid = value => Math.round(value * DRAG_SNAP) / DRAG_SNAP;

function setDragMode(on) {
  document.body.classList.toggle("drag-on", on);
  finishDrag();  // 中途关闭：这次移动照常结束并记录（所见即所存）
}

// 松手和中途关闭共用：拖过的才记；吞掉随后补出的 click，聚焦不会被触发
function finishDrag() {
  if (dragState?.moved) {
    dragSwallowClick = true;
    dragState.part.classList.remove("is-dragging");
    recordMove(dragState.part, dragState.dg);
  }
  dragState = null;
}

// 拖动范围：直接在图区里的，是整张网格；嵌套的，是父容器自己的宽高（坐标相对父容器）
function dragLimit(part, dg) {
  const parent = part.dataset.in && dg.querySelector(`:scope > [data-id="${CSS.escape(part.dataset.in)}"]`);
  const parentBox = parent && parseGridBox(parent.dataset.at);
  if (parentBox) return { columns: parentBox.width, rows: parentBox.height };
  const [columns, rows] = (dg.dataset.grid || DIAGRAM_DEFAULT_GRID).trim().split(/\s+/).map(Number);
  return { columns, rows };
}

// 吸附到 0.1 格后夹在 [0, 范围 - 自身尺寸] 里（上界也向下取到 0.1 格，吸附不会再把它推出界）
function snapInside(value, size, limit) {
  const highest = Math.max(0, Math.floor((limit - size) * DRAG_SNAP + 1e-9) / DRAG_SNAP);
  return Math.min(Math.max(snapToGrid(value), 0), highest);
}

function onDragPointerDown(event) {
  dragSwallowClick = false;
  if (!isDragOn() || event.button > 0 || dragState) return;  // 拖动进行中只认第一个指针
  const part = event.target.closest(".slide.active .dg > .dg-part[data-id]");
  if (!part || getComputedStyle(part).visibility === "hidden") return;  // 没揭示的分步元素不能拖
  const at = parseGridBox(part.dataset.at);
  if (!at) return;
  const dg = part.parentElement;
  dragState = { part, dg, pointerId: event.pointerId, startX: event.clientX, startY: event.clientY, at, moved: false, limit: dragLimit(part, dg),
    cell: { width: parseFloat(dg.style.getPropertyValue("--cell-w")), height: parseFloat(dg.style.getPropertyValue("--cell-h")) } };
}

function onDragPointerMove(event) {
  if (!dragState || event.pointerId !== dragState.pointerId) return;
  const screenX = event.clientX - dragState.startX, screenY = event.clientY - dragState.startY;
  if (!dragState.moved && Math.hypot(screenX, screenY) < DRAG_THRESHOLD_PX) return;
  if (!dragState.moved) {
    dragState.moved = true;
    clearFocus();  // focus.js：拖动时不留聚焦标记，重画的线才不会被压暗
    dragState.part.setPointerCapture(event.pointerId);
    dragState.part.classList.add("is-dragging");
  }
  const scale = stage.getBoundingClientRect().width / 1920;
  const { at, cell, part, dg } = dragState;
  const column = snapInside(at.column + screenX / scale / cell.width, at.width, dragState.limit.columns);
  const row = snapInside(at.row + screenY / scale / cell.height, at.height, dragState.limit.rows);
  part.dataset.at = `${column} ${row} ${at.width} ${at.height}`;
  redrawDiagram(dg);
  event.preventDefault();
}

function onDragPointerUp(event) {
  if (!dragState || event.pointerId !== dragState.pointerId) return;
  finishDrag();
}

// 位置按"来源文件 + 该文件里第几个 .dg + data-id"记，来源文件名由 build_deck.py 写在每页的 data-source 上
function recordMove(part, dg) {
  const slide = dg.closest(".slide");
  const source = slide.dataset.source || "";
  const diagram = slides.filter(other => (other.dataset.source || "") === source)
    .flatMap(other => [...other.querySelectorAll(".dg")]).indexOf(dg);
  dragMoves.set(`${source}|${diagram}|${part.dataset.id}`, { page: slides.indexOf(slide) + 1, source, diagram, id: part.dataset.id, at: part.dataset.at, was: dragSourceAt.get(part) ?? "" });
  document.body.classList.add("drag-has-moves");
}

function positionsFileText() {
  return JSON.stringify({ format: DRAG_POSITIONS_FORMAT, deck: document.title, moves: [...dragMoves.values()] }, null, 2) + "\n";
}

// Chrome（含 file:// 打开）用"另存为"对话框直接写文件；没有这个接口的浏览器下载一个同名文件
async function savePositions() {
  if (!dragMoves.size) return;
  const text = positionsFileText(), suggestedName = `${document.title}-位置.json`;
  if (window.showSaveFilePicker) {
    try {
      const handle = await window.showSaveFilePicker({ suggestedName, types: [{ description: "拖动后的位置", accept: { "application/json": [".json"] } }] });
      const writable = await handle.createWritable();
      await writable.write(text);
      await writable.close();
      return;
    } catch (error) {
      if (error.name === "AbortError") return;  // 用户在对话框里点了取消
    }
  }
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([text], { type: "application/json" }));
  link.download = suggestedName;
  link.click();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

// 拖完松手时浏览器还会补一次 click：在捕获阶段吞掉，聚焦（focus.js 的 document 冒泡监听）就收不到
function swallowClickAfterDrag(event) {
  if (!dragSwallowClick) return;
  dragSwallowClick = false;
  event.stopPropagation();
  event.preventDefault();
}

// 拖动模式下暂停触摸滑动翻页：runtime/deck.js 在 window 冒泡阶段监听 touchstart/touchend，这里在 window 捕获阶段先拦下
function pauseSwipeWhileDragging(event) {
  if (isDragOn()) event.stopPropagation();
}

function showDragButtonBriefly() {
  document.body.classList.add("drag-button-shown");
  clearTimeout(dragIdleTimer);
  dragIdleTimer = setTimeout(() => document.body.classList.remove("drag-button-shown"), DRAG_BUTTON_IDLE_MS);
}

// 只有含图元的课件才有"拖动"按钮；按钮平时隐藏，指针动一下才出现（回归截图里没有它）
function addDragButton() {
  if (!document.querySelector(".slide .dg")) return;
  const button = document.createElement("button");
  button.id = "drag-toggle";
  button.textContent = "拖动";
  button.addEventListener("click", () => setDragMode(!isDragOn()));
  const saveButton = document.createElement("button");
  saveButton.id = "drag-save";
  saveButton.textContent = "保存位置";
  saveButton.addEventListener("click", savePositions);
  stage.append(button, saveButton);
  addEventListener("pointermove", showDragButtonBriefly);
  addEventListener("pointerdown", showDragButtonBriefly);
}

addEventListener("pointerdown", onDragPointerDown);
addEventListener("pointermove", onDragPointerMove);
addEventListener("pointerup", onDragPointerUp);
addEventListener("pointercancel", onDragPointerUp);
addEventListener("click", swallowClickAfterDrag, true);
addEventListener("touchstart", pauseSwipeWhileDragging, true);
addEventListener("touchend", pauseSwipeWhileDragging, true);
document.addEventListener("keydown", event => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "s" && isDragOn()) {
    event.preventDefault();  // 拖动模式下 Ctrl/Cmd+S 存位置，不弹浏览器的"网页另存为"
    savePositions();
    return;
  }
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  if (event.key.toLowerCase() === DRAG_TOGGLE_KEY) setDragMode(!isDragOn());
});
// 翻页自动关拖动模式（Q-019 第 12 问）；拖到一半翻页，这次移动照常结束并记录
(window.componentEnterSteps = window.componentEnterSteps || []).push(() => setDragMode(false));
// Esc 关拖动模式并且不再取消聚焦：window 捕获阶段先于 focus.js 的 document 监听；页面地图开着时留给地图（先关地图）
addEventListener("keydown", event => {
  if (event.key !== "Escape" || event.metaKey || event.ctrlKey || event.altKey) return;
  if (!isDragOn() || document.body.classList.contains("map-open")) return;
  setDragMode(false);
  event.stopPropagation();
}, true);
(window.componentBootSteps = window.componentBootSteps || []).push(addDragButton);
