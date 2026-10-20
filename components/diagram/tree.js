// 图元 · 树布局（Q-017 D3：手写，不引入 dagre）：.dg[data-tree="down|right|mind"] 里作者只写节点和 data-parent，
// 放映启动时（render.js 之前）算出每个节点的 data-at、生成父 → 子连线，再由 render.js 照常画。
// 作者自己写了 data-at 的节点保留原位（拖动存回的位置就是这样生效的），连线照样生成。
const TREE_DEFAULT_NODE = "4 1.4";   // 节点 宽 高（网格），.dg 上 data-node 可改，节点上 data-size 可单独改
const TREE_DEFAULT_GAP = "1.5 0.5";  // 层距 兄弟距（网格），.dg 上 data-gap 可改
const TREE_EDGE_SIDES = { down: ["b", "t"], right: ["r", "l"], left: ["l", "r"] };
const TREE_DIRECTIONS = ["down", "right", "mind"];
const TREE_ROUTES = { down: "ortho", right: "ortho", mind: "curve" };  // 思维导图用曲线，其余用折线总线（检查点 C 看观感）
const TREE_PRECISION = 1000;

const treeRound = value => Math.round(value * TREE_PRECISION) / TREE_PRECISION;

// 找根、查父节点，返回 { root, children: Map(id → [子节点…]), problems }
function treeStructure(nodes) {
  const byId = new Map(nodes.map(node => [node.id, node]));
  const problems = [];
  const children = new Map(nodes.map(node => [node.id, []]));
  let root = null;
  nodes.forEach(node => {
    if (!node.parent) {
      if (root) problems.push({ id: node.id, problem: `树只能有一个根，已有 ${root.id}` });
      else root = node;
    } else if (!byId.has(node.parent)) problems.push({ id: node.id, problem: `父节点 ${node.parent} 不存在` });
    else children.get(node.parent).push(node);
  });
  return { root, children, problems };
}

// 一侧的子树：breadth 是兄弟排开的方向，depth 是层的方向。先量每棵子树：占宽 span、节点中心离占宽起点的距离 centerOf、
// 孩子块离占宽起点的距离 kidsOffsetOf。父节点居中在首末孩子中心的中点；父节点比孩子块宽、或中点偏出孩子块时，
// 占宽向外撑开（而不是把父节点夹回去），这样父节点始终居中，也不会压到相邻兄弟的子树。再从左到右（从上到下）摆
function placeSide(rootNode, sideChildren, children, axes, gap, placed) {
  const breadthOf = node => node.size[axes.breadth];
  const spanOf = new Map(), centerOf = new Map(), kidsOffsetOf = new Map();
  const measure = node => {
    const kids = children.get(node.id);
    if (!kids.length) {
      spanOf.set(node.id, breadthOf(node));
      centerOf.set(node.id, breadthOf(node) / 2);
      return spanOf.get(node.id);
    }
    let cursor = 0;
    const kidCenters = kids.map(kid => { measure(kid); const center = cursor + centerOf.get(kid.id); cursor += spanOf.get(kid.id) + gap.sibling; return center; });
    const kidsSpan = cursor - gap.sibling;
    const center = (kidCenters[0] + kidCenters[kidCenters.length - 1]) / 2;
    const left = Math.min(0, center - breadthOf(node) / 2), right = Math.max(kidsSpan, center + breadthOf(node) / 2);
    spanOf.set(node.id, right - left);
    centerOf.set(node.id, center - left);
    kidsOffsetOf.set(node.id, -left);
    return right - left;
  };
  // 子树占 [start, start + 占宽]；返回这个节点中心的位置
  const place = (node, start, level) => {
    const entry = { node, level, breadthStart: start + centerOf.get(node.id) - breadthOf(node) / 2 };
    placed.push(entry);
    let cursor = start + (kidsOffsetOf.get(node.id) || 0);
    children.get(node.id).forEach(kid => { place(kid, cursor, level + 1); cursor += spanOf.get(kid.id) + gap.sibling; });
    return start + centerOf.get(node.id);
  };
  const blockSpan = sideChildren.reduce((total, kid) => total + measure(kid), 0) + gap.sibling * Math.max(0, sideChildren.length - 1);
  const firstEntry = placed.length;
  let cursor = (breadthOf(rootNode) - blockSpan) / 2;
  const rootKidCenters = sideChildren.map(kid => { const center = place(kid, cursor, 1); cursor += spanOf.get(kid.id) + gap.sibling; return center; });
  if (!rootKidCenters.length) return;
  // 这一侧整块平移，让根的首末孩子中心的中点对准根的中线
  const shift = breadthOf(rootNode) / 2 - (rootKidCenters[0] + rootKidCenters[rootKidCenters.length - 1]) / 2;
  placed.slice(firstEntry).forEach(entry => { entry.breadthStart += shift; });
}

// 思维导图：根的孩子写了 data-side="l|r" 的按写的放；其余前一半（向上取整）放右边、后一半放左边
function splitMindChildren(rootChildren) {
  const free = rootChildren.filter(kid => kid.side !== "l" && kid.side !== "r");
  const rightFree = new Set(free.slice(0, Math.ceil(free.length / 2)));
  return {
    right: rootChildren.filter(kid => kid.side === "r" || rightFree.has(kid)),
    left: rootChildren.filter(kid => kid.side === "l" || (!rightFree.has(kid) && kid.side !== "r")),
  };
}

// nodes：[{ id, parent, side, size: { w, h } }]（文档顺序），parent 为空的是根；direction："down" | "right" | "mind"
// gap：{ level, sibling }（网格）。返回 { boxes: { id: { column, row, width, height } }, edges: [{ from, to, fromSide, toSide }],
// extent: { columns, rows }, problems: [{ id, problem }] }；坐标已平移到从 0 起，没有居中
function layoutTree(nodes, direction, gap) {
  if (!TREE_DIRECTIONS.includes(direction)) {
    const reason = `未知 data-tree 值 ${direction}（只能写 ${TREE_DIRECTIONS.join("、")}）`;
    return { boxes: {}, edges: [], extent: { columns: 0, rows: 0 }, problems: nodes.map(node => ({ id: node.id, problem: reason })) };
  }
  const { root, children, problems } = treeStructure(nodes);
  const vertical = direction === "down";
  const axes = vertical ? { breadth: "w", depth: "h" } : { breadth: "h", depth: "w" };
  const placed = [];
  if (root) {
    placed.push({ node: root, level: 0, breadthStart: 0, side: "right" });
    const sides = direction === "mind" ? splitMindChildren(children.get(root.id)) : { right: children.get(root.id), left: [] };
    ["right", "left"].forEach(side => {
      const from = placed.length;
      placeSide(root, sides[side], children, axes, gap, placed);
      placed.slice(from).forEach(entry => { entry.side = side; });
    });
  }
  const placedIds = new Set(placed.map(entry => entry.node.id));
  nodes.filter(node => !placedIds.has(node.id) && !problems.some(problem => problem.id === node.id))
    .forEach(node => problems.push({ id: node.id, problem: "不在树上（父节点成环，或没有根）" }));
  // 每层的深度 = 这层最大的节点；层的起点 = 前面各层深度 + 层距
  const levelDepth = [];
  placed.forEach(({ node, level }) => { levelDepth[level] = Math.max(levelDepth[level] || 0, node.size[axes.depth]); });
  const levelStart = levelDepth.map((_, level) => levelDepth.slice(0, level).reduce((total, depth) => total + depth + gap.level, 0));
  const rootDepth = levelDepth[0] || 0;
  const raw = placed.map(({ node, level, breadthStart, side }) => {
    const depthSize = node.size[axes.depth];
    const depthStart = side === "left" ? rootDepth - levelStart[level] - depthSize : levelStart[level];
    const [column, row] = vertical ? [breadthStart, depthStart] : [depthStart, breadthStart];
    return { node, side, box: { column, row, width: node.size.w, height: node.size.h } };
  });
  const minColumn = Math.min(0, ...raw.map(entry => entry.box.column)), minRow = Math.min(0, ...raw.map(entry => entry.box.row));
  const placedBox = new Map(raw.map(entry => [entry.node.id, entry]));
  const boxes = {};
  nodes.filter(node => placedBox.has(node.id)).forEach(node => {
    const { box } = placedBox.get(node.id);
    boxes[node.id] = { column: treeRound(box.column - minColumn), row: treeRound(box.row - minRow), width: box.width, height: box.height };
  });
  const edges = nodes.filter(node => node.parent && placedBox.has(node.id)).map(node => {
    const sideName = vertical ? "down" : placedBox.get(node.id).side === "left" ? "left" : "right";
    const [fromSide, toSide] = TREE_EDGE_SIDES[sideName];
    return { from: node.parent, to: node.id, fromSide, toSide };
  });
  const extent = {
    columns: treeRound(Math.max(0, ...Object.values(boxes).map(box => box.column + box.width))),
    rows: treeRound(Math.max(0, ...Object.values(boxes).map(box => box.row + box.height))),
  };
  return { boxes, edges, extent, problems };
}

function parsePair(text) {
  const numbers = String(text || "").trim().split(/\s+/).map(Number);
  return numbers.length === 2 && numbers.every(Number.isFinite) ? numbers : null;
}

// 把一张树图的布局写回 DOM：节点的 data-at（作者写过的不动）、连线 <i class="edge">；排不上的节点把原因写进 data-at，
// render.js 会报"data-at 要写 4 个数：树布局：…"（带页码和 id），预览因此失败
function applyTreeLayout(dg) {
  const direction = dg.dataset.tree;
  const [columns, rows] = (dg.dataset.grid || DIAGRAM_DEFAULT_GRID).trim().split(/\s+/).map(Number);
  const [nodeWidth, nodeHeight] = parsePair(dg.dataset.node) || parsePair(TREE_DEFAULT_NODE);
  const [levelGap, siblingGap] = parsePair(dg.dataset.gap) || parsePair(TREE_DEFAULT_GAP);
  const elements = [...dg.querySelectorAll(":scope > .node")];
  const nodes = elements.map(element => {
    const [w, h] = parsePair(element.dataset.size) || [nodeWidth, nodeHeight];
    return { id: element.dataset.id, parent: element.dataset.parent || null, side: element.dataset.side || null, size: { w, h } };
  });
  const tree = layoutTree(nodes, direction, { level: levelGap, sibling: siblingGap });
  const offsetColumn = (columns - tree.extent.columns) / 2, offsetRow = (rows - tree.extent.rows) / 2;
  const problemOf = new Map(tree.problems.map(problem => [problem.id, problem.problem]));
  elements.forEach(element => {
    if (element.dataset.at) return;
    const box = tree.boxes[element.dataset.id];
    element.dataset.at = box ? [box.column + offsetColumn, box.row + offsetRow, box.width, box.height].map(treeRound).join(" ")
      : `树布局：${problemOf.get(element.dataset.id)}`;
  });
  tree.edges.forEach(edge => {
    const wire = document.createElement("i");
    wire.className = "edge";
    Object.assign(wire.dataset, { from: `${edge.from}:${edge.fromSide}`, to: `${edge.to}:${edge.toSide}`, end: "none",
      route: TREE_ROUTES[direction] || "ortho", trunk: "" });
    dg.append(wire);
  });
}

function applyAllTreeLayouts() {
  document.querySelectorAll(".slide .dg[data-tree]").forEach(applyTreeLayout);
}

(window.componentBootSteps = window.componentBootSteps || []).push(applyAllTreeLayouts);
