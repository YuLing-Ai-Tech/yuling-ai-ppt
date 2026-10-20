// 图元 · 循环图（Q-017 D6）：.dg[data-cycle] 里的节点按文档顺序，从正上方起顺时针排在椭圆上；相邻两个之间连一条曲线箭头，
// 最后一个连回第一个。data-center 的节点放在正中、不进环。作者写了 data-at 的节点保留原位，连线照样生成
const CYCLE_DEFAULT_NODE = "4 1.6";  // 节点 宽 高（网格），.dg 上 data-node 可改
const CYCLE_MARGIN = 0.3;            // 环离图区边的余量（网格）
const CYCLE_SIDE_ORDER = ["r", "b", "l", "t"];  // 两条边一样好时取靠前的
const CYCLE_MAX_NODES = 12;          // 环上最多几个节点：24×12 图区、4×1.6 的节点到 12 个不重叠，再多会叠（评审实测 14 个有 4 对重叠）
const CYCLE_PRECISION = 1000;

const cycleRound = value => Math.round(value * CYCLE_PRECISION) / CYCLE_PRECISION;

// count 个节点在 grid（{ columns, rows }）里的格子坐标，size：{ w, h }；返回 [{ column, row, width, height, angle }]
function layoutCycle(count, grid, size) {
  const radiusX = grid.columns / 2 - size.w / 2 - CYCLE_MARGIN, radiusY = grid.rows / 2 - size.h / 2 - CYCLE_MARGIN;
  return Array.from({ length: count }, (_, index) => {
    const angle = -Math.PI / 2 + index * 2 * Math.PI / count;
    return { column: cycleRound(grid.columns / 2 + radiusX * Math.cos(angle) - size.w / 2),
      row: cycleRound(grid.rows / 2 + radiusY * Math.sin(angle) - size.h / 2), width: size.w, height: size.h, angle };
  });
}

// 方向向量最接近哪条边（SIDE_VECTORS 在 route.js）
function nearestSide(vector) {
  let best = CYCLE_SIDE_ORDER[0], bestScore = -Infinity;
  CYCLE_SIDE_ORDER.forEach(side => {
    const score = SIDE_VECTORS[side].x * vector.x + SIDE_VECTORS[side].y * vector.y;
    if (score > bestScore + 1e-9) { best = side; bestScore = score; }
  });
  return best;
}

// 顺时针的切线方向：出口取起点切线最近的边，入口取终点切线反方向最近的边（线顺着环的方向进来）
function cycleEdgeSides(fromAngle, toAngle) {
  const tangent = angle => ({ x: -Math.sin(angle), y: Math.cos(angle) });
  const into = tangent(toAngle);
  return [nearestSide(tangent(fromAngle)), nearestSide({ x: -into.x, y: -into.y })];
}

// 返回 [[节点, 原因]…]；能排返回 null。排不了时整图不排，图里每个节点（含中心节点）都报原因，免得没问题的节点显示成"（空）"
function cycleRefusal(dg, ring) {
  const nodes = [...dg.querySelectorAll(":scope > .node")];
  if (nodes.some(element => !element.dataset.id)) {
    return nodes.map(element => [element, element.dataset.id ? "同图有节点缺 data-id，整图未排" : "节点缺 data-id"]);
  }
  return ring.length > CYCLE_MAX_NODES ? nodes.map(element => [element, `环上有 ${ring.length} 个节点，最多 ${CYCLE_MAX_NODES} 个，整图未排`]) : null;
}

function applyCycleLayout(dg) {
  const [columns, rows] = (dg.dataset.grid || DIAGRAM_DEFAULT_GRID).trim().split(/\s+/).map(Number);
  const [width, height] = (dg.dataset.node || CYCLE_DEFAULT_NODE).trim().split(/\s+/).map(Number);
  const ring = [...dg.querySelectorAll(":scope > .node:not([data-center])")];
  // 排不了的情形把原因写进 data-at，render.js 报"data-at 要写 4 个数：循环图：…"（带页码和 id），预览因此失败
  const refusal = cycleRefusal(dg, ring);
  if (refusal) { refusal.forEach(([element, reason]) => { if (!element.dataset.at) element.dataset.at = `循环图：${reason}`; }); return; }
  const places = layoutCycle(ring.length, { columns, rows }, { w: width, h: height });
  ring.forEach((element, index) => {
    if (!element.dataset.at) element.dataset.at = [places[index].column, places[index].row, width, height].join(" ");
  });
  dg.querySelectorAll(":scope > .node[data-center]").forEach(element => {
    const [centerWidth, centerHeight] = (element.dataset.size || `${width} ${height}`).trim().split(/\s+/).map(Number);
    if (!element.dataset.at) element.dataset.at = [cycleRound((columns - centerWidth) / 2), cycleRound((rows - centerHeight) / 2), centerWidth, centerHeight].join(" ");
  });
  if (ring.length < 2) return;
  ring.forEach((element, index) => {
    const next = ring[(index + 1) % ring.length];
    const [fromSide, toSide] = cycleEdgeSides(places[index].angle, places[(index + 1) % ring.length].angle);
    const wire = document.createElement("i");
    wire.className = "edge";
    Object.assign(wire.dataset, { from: `${element.dataset.id}:${fromSide}`, to: `${next.dataset.id}:${toSide}`, route: "curve" });
    dg.append(wire);
  });
}

function applyAllCycleLayouts() {
  document.querySelectorAll(".slide .dg[data-cycle]").forEach(applyCycleLayout);
}

(window.componentBootSteps = window.componentBootSteps || []).push(applyAllCycleLayouts);
