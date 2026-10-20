// 图元 · 渲染：把 .dg 里作者写的容器、节点、连线摆上网格、画出连线，再跑连线检查；问题汇总到 window.diagramProblems
const DIAGRAM_DEFAULT_GRID = "24 12";
const DIAGRAM_CONTAINER_SELECTOR = ".zone, .lane, .quadrant";
const DIAGRAM_BOX_SELECTOR = ".zone, .lane, .quadrant, .node, .axis, .legend";
const DIAGRAM_SVG_NS = "http://www.w3.org/2000/svg";
const DIAGRAM_KINDS = Object.keys(DIAGRAM_KIND_NAMES);  // 连线类型只在 atoms.js 的 DIAGRAM_KIND_NAMES 定义一处
const DIAGRAM_END_SHAPES = { arrow: "M0 1 L10 5 L0 9 Z", dot: "M1 5 A4 4 0 1 1 9 5 A4 4 0 1 1 1 5 Z", diamond: "M0 5 L5 1 L10 5 L5 9 Z" };
const DIAGRAM_END_NAMES = [...Object.keys(DIAGRAM_END_SHAPES), "none"];
const DIAGRAM_TONES = ["1", "2", "3", "4", "5", "6", "7", "8"];  // 与 diagram.css 的 [data-tone="1"]～"8" 对应
const DIAGRAM_PACKET_SPACING = 380;
const DIAGRAM_TAB_HALF_HEIGHT = 14;

function boxRole(element) {
  if (element.matches(DIAGRAM_CONTAINER_SELECTOR)) return "container";
  return element.matches(".node") ? "node" : "decor";
}

function readBoxes(dg) {
  return [...dg.querySelectorAll(DIAGRAM_BOX_SELECTOR)].map((element, index) => ({
    element, id: element.dataset.id || `#${index + 1}`, parent: element.dataset.in || null,
    role: boxRole(element), at: parseGridBox(element.dataset.at) }));
}

// 步骤、色调没写就沿 data-in 向上继承父容器的
function inheritFromParents(boxes) {
  const byId = new Map(boxes.map(box => [box.id, box]));
  const lookUp = (box, name, seen = new Set()) => {
    if (box.element.dataset[name] || !box.parent || seen.has(box.id)) return box.element.dataset[name] || "";
    const parent = byId.get(box.parent);
    return parent ? lookUp(parent, name, seen.add(box.id)) : "";
  };
  boxes.forEach(box => ["step", "tone"].forEach(name => {
    const value = lookUp(box, name);
    if (value) box.element.dataset[name] = value;
  }));
}

function placeBoxes(boxes, layout) {
  boxes.forEach(box => {
    const rect = layout.rects[box.id];
    if (!rect) return;
    box.element.classList.add("dg-part");
    Object.assign(box.element.style, { left: `${rect.x}px`, top: `${rect.y}px`, width: `${rect.w}px`, height: `${rect.h}px` });
    if (box.role === "container") box.element.style.zIndex = 1 + layout.depths[box.id];
  });
}

// 节点内部：图标 + 文字；data-flow 的节点加一圈呼吸光环（脉冲）
function decorateNodes(boxes) {
  boxes.filter(box => box.role === "node").forEach((box, index) => {
    const node = box.element;
    const text = document.createElement("div");
    text.className = "text";
    text.append(...node.childNodes);
    if (node.dataset.icon) {
      const icon = document.createElement("i");
      icon.className = "ic";
      icon.textContent = node.dataset.icon;
      node.append(icon);
    }
    node.append(text);
    if (node.hasAttribute("data-flow")) node.insertAdjacentHTML("beforeend", '<span class="halo" data-flow></span>');
    node.style.setProperty("--delay", `${0.1 + index * 0.035}s`);
  });
}

// 连线 id "from→to"：连线检查、图元零件的 data-edge、聚焦都用它认同一条线
function edgeIdOf(edgeElement) {
  return `${parseEndpoint(edgeElement.dataset.from).id}→${parseEndpoint(edgeElement.dataset.to).id}`;
}

// 写法错误：色调、线端形状、路径拼错或缺属性时，画面会悄悄退回默认，所以都进问题清单（带页码和 id）
function toneProblems(boxes) {
  return boxes.filter(box => box.element.dataset.tone && !DIAGRAM_TONES.includes(box.element.dataset.tone))
    .map(box => ({ id: box.id, problem: `色调 ${box.element.dataset.tone} 未知（可用 1～8）` }));
}

function lineEndProblems(edges) {
  return edges.flatMap(edge => [["data-start", edge.element.dataset.start], ["data-end", edge.element.dataset.end]]
    .filter(([, shape]) => shape && !DIAGRAM_END_NAMES.includes(shape))
    .map(([name, shape]) => ({ id: edge.id, problem: `${name} ${shape} 未知（可用 ${DIAGRAM_END_NAMES.join("、")}）` })));
}

// 连线 id 是 "起点→终点"，同方向两条线 id 相同，连线检查和聚焦分不开；线没有 data-id 机制，所以只报问题
function duplicateEdgeProblems(edges) {
  const counts = new Map();
  edges.forEach(edge => counts.set(edge.id, (counts.get(edge.id) || 0) + 1));
  return [...counts].filter(([, count]) => count > 1)
    .map(([id, count]) => ({ id, problem: `同方向的连线有 ${count} 条，检查和聚焦按「起点→终点」认线，请合并成一条` }));
}

function routeProblems(dg, boxes) {
  const known = new Set(boxes.map(box => box.id));
  return [...dg.querySelectorAll(".route")].flatMap((route, index) => {
    const nodeIds = (route.dataset.nodes || "").trim().split(/\s+/).filter(Boolean);
    if (!nodeIds.length) return [{ id: `路径 ${index + 1}`, problem: "缺 data-nodes" }];
    return nodeIds.filter(nodeId => !known.has(nodeId)).map(nodeId => ({ id: `路径 ${index + 1}`, problem: `节点 ${nodeId} 不存在` }));
  });
}

function readEdges(dg, rects, cell) {
  return [...dg.querySelectorAll(".edge")].map(element => {
    const from = parseEndpoint(element.dataset.from), to = parseEndpoint(element.dataset.to);
    return { element, from, to, id: edgeIdOf(element), kind: element.dataset.kind || "sync", label: element.dataset.label || "",
      route: element.dataset.route || "ortho", vias: parseVias(element.dataset.via, cell), fromRect: rects[from.id], toRect: rects[to.id] };
  });
}

// 选边、错开端口、算路径；两端有一端不存在的线跳过（连线检查会报出来）
function routeEdges(edges) {
  const drawable = edges.filter(edge => edge.fromRect && edge.toRect);
  const ends = [];
  drawable.forEach(edge => {
    const [autoFrom, autoTo] = autoSides(edge.fromRect, edge.toRect);
    edge.fromSide = edge.from.side || autoFrom;
    edge.toSide = edge.to.side || autoTo;
    ends.push({ key: `${edge.from.id}:${edge.fromSide}`, otherCenter: rectCenter(edge.toRect) },
      { key: `${edge.to.id}:${edge.toSide}`, otherCenter: rectCenter(edge.fromRect) });
  });
  const offsets = portOffsets(ends);
  drawable.forEach((edge, index) => {
    // data-trunk（树布局生成的线）：同一父节点出去的线共用一个出口，汇成总线，不按 DIAGRAM_PORT_GAP 错开
    const fromOffset = edge.element.hasAttribute("data-trunk") ? 0 : offsets[index * 2], toOffset = offsets[index * 2 + 1];
    edge.geometry = routeEdge({ start: anchorPoint(edge.fromRect, edge.fromSide, fromOffset), startSide: edge.fromSide,
      end: anchorPoint(edge.toRect, edge.toSide, toOffset), endSide: edge.toSide, vias: edge.vias, endOffset: toOffset, route: edge.route });
  });
  return drawable;
}

function makeLayers(dg, canvas) {
  const svg = document.createElementNS(DIAGRAM_SVG_NS, "svg");
  svg.setAttribute("class", "dg-wires");
  svg.setAttribute("viewBox", `0 0 ${canvas.w} ${canvas.h}`);
  const packets = document.createElement("div");
  packets.className = "dg-packets";
  const labels = document.createElement("div");
  labels.className = "dg-labels";
  dg.append(svg, packets, labels);
  return { svg, packets, labels };
}

function edgePath(svg, className, pathData) {
  const path = document.createElementNS(DIAGRAM_SVG_NS, "path");
  path.setAttribute("class", className);
  path.setAttribute("d", pathData);
  svg.append(path);
  return path;
}

function drawEdge(layers, edge, order) {
  const { element, geometry, kind } = edge;
  const wire = edgePath(layers.svg, "wire", geometry.pathData);
  const length = wire.getTotalLength();
  const tip = edgePath(layers.svg, "tip", geometry.pathData);
  const endShape = element.dataset.end || "arrow", startShape = element.dataset.start;
  if (DIAGRAM_END_SHAPES[endShape]) tip.setAttribute("marker-end", `url(#dg-end-${endShape}-${kind})`);
  if (DIAGRAM_END_SHAPES[startShape]) tip.setAttribute("marker-start", `url(#dg-end-${startShape}-${kind})`);
  if (element.dataset.line) wire.dataset.line = element.dataset.line;
  const parts = [wire, tip];
  if (element.hasAttribute("data-flow")) parts.push(...drawFlow(layers, edge, length));
  if (edge.label) parts.push(drawLabel(layers, edge));
  const step = element.dataset.step || String(Math.max(Number(edge.fromStep) || 0, Number(edge.toStep) || 0) || "");
  parts.forEach(part => {
    part.classList.add("dg-part");
    part.dataset.kind = kind;
    part.dataset.edge = edge.id;
    if (step) part.dataset.step = step;
    part.style.setProperty("--len", length);
    part.style.setProperty("--delay", `${0.5 + order * 0.02}s`);
  });
  return parts;
}

// 流动（设计 §3.2）：虚线沿线流动；data-flow="packet" 再加沿路径跑的数据包。时长由 CSS 按 --flow-speed 算
function drawFlow(layers, edge, length) {
  const flowline = edgePath(layers.svg, "flowline", edge.geometry.pathData);
  flowline.setAttribute("data-flow", "");
  const parts = [flowline];
  if (edge.element.dataset.flow !== "packet") return parts;
  const count = Math.max(1, Math.round(length / DIAGRAM_PACKET_SPACING));
  for (let index = 0; index < count; index++) {
    const packet = document.createElement("i");
    packet.className = "packet";
    packet.setAttribute("data-flow", "");
    packet.style.offsetPath = `path("${edge.geometry.pathData}")`;
    packet.style.setProperty("--packet-phase", index / count);
    layers.packets.append(packet);
    parts.push(packet);
  }
  return parts;
}

function drawLabel(layers, edge) {
  const label = document.createElement("span");
  label.className = "dg-label";
  label.textContent = edge.label;
  label.style.left = `${edge.geometry.labelAt.x}px`;
  label.style.top = `${edge.geometry.labelAt.y}px`;
  layers.labels.append(label);
  return label;
}

// 标签的外框：CSS 用 translate(-50%, -50%) 居中，这里按未变形的尺寸算，不受登场动画影响
function labelRects(edges) {
  return edges.filter(edge => edge.label).map(edge => {
    const label = edge.labelElement;
    const width = label.offsetWidth, height = label.offsetHeight;
    return { id: `${edge.id} 的标签`, rect: { x: edge.geometry.labelAt.x - width / 2, y: edge.geometry.labelAt.y - height / 2, w: width, h: height } };
  });
}

function placeTabs(boxes, rects, edges) {
  const polylines = edges.map(edge => edge.geometry.points);
  boxes.filter(box => box.role === "container" && rects[box.id]).forEach(box => {
    const tab = box.element.querySelector(":scope > .tab");
    if (!tab || box.element.classList.contains("tab-bottom")) return;
    const rect = rects[box.id];
    const topRect = { x: rect.x + tab.offsetLeft, y: rect.y - DIAGRAM_TAB_HALF_HEIGHT, w: tab.offsetWidth, h: tab.offsetHeight };
    const bottomRect = { ...topRect, y: rect.y + rect.h - DIAGRAM_TAB_HALF_HEIGHT };
    if (chooseTabSide(topRect, bottomRect, polylines) === "bottom") box.element.classList.add("tab-bottom");
  });
}

// 连线的步骤取两端里靠后的那一步；画好的线带上自己的零件（.wire、.tip、流动、标签），返回画出来的线
function drawEdges(dg, canvas, boxes, edges) {
  const stepOf = new Map(boxes.map(box => [box.id, box.element.dataset.step]));
  edges.forEach(edge => { edge.fromStep = stepOf.get(edge.from.id); edge.toStep = stepOf.get(edge.to.id); });
  const layers = makeLayers(dg, canvas);
  const drawn = routeEdges(edges);
  drawn.forEach((edge, order) => {
    edge.parts = drawEdge(layers, edge, order);
    edge.labelElement = edge.parts.find(part => part.classList.contains("dg-label"));
  });
  return drawn;
}

function renderDiagram(dg) {
  const [columns, rows] = (dg.dataset.grid || DIAGRAM_DEFAULT_GRID).trim().split(/\s+/).map(Number);
  const canvas = { x: 0, y: 0, w: dg.clientWidth, h: dg.clientHeight };
  const cell = { width: canvas.w / columns, height: canvas.h / rows };
  dg.style.setProperty("--cell-w", `${cell.width}px`);
  dg.style.setProperty("--cell-h", `${cell.height}px`);
  const boxes = readBoxes(dg);
  const problems = boxes.filter(box => !box.at).map(box => ({ id: box.id, problem: `data-at 要写 4 个数：${box.element.dataset.at || "（空）"}` }));
  boxes.filter(box => box.element.parentElement !== dg).forEach(box => problems.push({ id: box.id, problem: "要直接写在 .dg 下，嵌套用 data-in" }));
  problems.push(...toneProblems(boxes));
  const laidOut = boxes.filter(box => box.at);
  const layout = layoutBoxes(laidOut, cell);
  problems.push(...layout.problems);
  inheritFromParents(laidOut);
  placeBoxes(laidOut, layout);
  decorateNodes(laidOut);
  decorateAtoms(laidOut);
  const edges = readEdges(dg, layout.rects, cell);
  edges.filter(edge => !DIAGRAM_KINDS.includes(edge.kind)).forEach(edge =>
    problems.push({ id: edge.id, problem: `连线类型 ${edge.kind} 未知（可用 ${DIAGRAM_KINDS.join("、")}）` }));
  problems.push(...lineEndProblems(edges), ...duplicateEdgeProblems(edges), ...routeProblems(dg, boxes));
  const drawn = drawEdges(dg, canvas, laidOut, edges);
  placeTabs(laidOut, layout.rects, drawn);
  problems.push(...findDiagramProblems({ boxes: laidOut, rects: layout.rects, canvas,
    edges: edges.map(edge => ({ id: edge.id, from: edge.from.id, to: edge.to.id })), labels: labelRects(drawn) }));
  return problems;
}

// 拖动后重画一张图（drag.js 调）：按当前 data-at 重新摆盒子、重画全部连线；不再装饰节点（renderDiagram 已做过）。
// 新画的线跳过登场动画（--delay 拨到 -10s，动画一开始就已结束）；分步揭示按本页当前进度重新标 .step-shown（runtime/steps.js）
const DIAGRAM_REDRAW_DELAY = "-10s";

function redrawDiagram(dg) {
  dg.querySelectorAll(":scope > .dg-wires, :scope > .dg-packets, :scope > .dg-labels").forEach(layer => layer.remove());
  const canvas = { x: 0, y: 0, w: dg.clientWidth, h: dg.clientHeight };
  const cell = { width: parseFloat(dg.style.getPropertyValue("--cell-w")), height: parseFloat(dg.style.getPropertyValue("--cell-h")) };
  const boxes = readBoxes(dg).filter(box => box.at);
  const layout = layoutBoxes(boxes, cell);
  placeBoxes(boxes, layout);
  drawEdges(dg, canvas, boxes, readEdges(dg, layout.rects, cell))
    .forEach(edge => edge.parts.forEach(part => part.style.setProperty("--delay", DIAGRAM_REDRAW_DELAY)));
  const slide = dg.closest(".slide");
  if (stepCount(slide)) setShownStep(slide, shownSteps.get(slide) ?? stepCount(slide), false);
}

// 箭头、圆点、菱形端点：全课件共用一份，放在舞台上（不在任何一页里），缩略图副本引用时也能显示
function addEndMarkers() {
  const defs = document.createElementNS(DIAGRAM_SVG_NS, "svg");
  defs.setAttribute("class", "dg-defs");
  defs.innerHTML = "<defs>" + DIAGRAM_KINDS.flatMap(kind => Object.entries(DIAGRAM_END_SHAPES).map(([shape, pathData]) =>
    `<marker id="dg-end-${shape}-${kind}" data-kind="${kind}" viewBox="0 0 10 10" refX="${shape === "arrow" ? 9 : 5}" refY="5"` +
    ` markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" orient="auto-start-reverse"><path d="${pathData}"/></marker>`)).join("") + "</defs>";
  document.getElementById("stage").prepend(defs);
}

function renderAllDiagrams() {
  window.diagramProblems = [];
  const pages = slides.map((slide, index) => ({ page: index + 1, diagrams: [...slide.querySelectorAll(".dg")] }))
    .filter(page => page.diagrams.length);
  if (!pages.length) return;
  addEndMarkers();
  pages.forEach(({ page, diagrams }) => diagrams.forEach(dg => renderDiagram(dg).forEach(problem => {
    window.diagramProblems.push({ page, ...problem });
    console.error(`连线检查：第 ${page} 页 ${problem.id}：${problem.problem}`);
  })));
}

(window.componentBootSteps = window.componentBootSteps || []).push(renderAllDiagrams);
