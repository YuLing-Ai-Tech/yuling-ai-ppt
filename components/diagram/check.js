// 图元 · 连线检查（设计 §4.5）：连线端点存在、同一容器里不重叠、不超出父容器、标签不压节点。纯函数，不碰 DOM
// boxes：[{ id, parent, role }]，role 是 container（容器、泳道、象限）、node（节点）或 decor（图例、时间轴，只查不出界）
// rects：layoutBoxes 的结果；canvas：图区 { x: 0, y: 0, w, h }；edges：[{ id, from, to }]；labels：[{ id, rect }]
function findDiagramProblems({ boxes, rects, canvas, edges, labels }) {
  const problems = [];
  const known = new Set(boxes.map(box => box.id));
  edges.forEach(edge => [edge.from, edge.to].forEach(end => {
    if (!known.has(end)) problems.push({ id: edge.id, problem: `连线端点 ${end} 不存在` });
  }));
  const placed = boxes.filter(box => rects[box.id]);
  placed.forEach(box => {
    const parentRect = box.parent ? rects[box.parent] : canvas;
    if (parentRect && !rectInside(rects[box.id], parentRect)) {
      problems.push({ id: box.id, problem: box.parent ? `超出父容器 ${box.parent}` : "超出图区" });
    }
  });
  const solid = placed.filter(box => box.role !== "decor");
  solid.forEach((first, index) => solid.slice(index + 1).forEach(second => {
    if ((first.parent || null) === (second.parent || null) && rectsOverlap(rects[first.id], rects[second.id])) {
      problems.push({ id: `${first.id} × ${second.id}`, problem: "同一容器里重叠" });
    }
  }));
  const nodes = placed.filter(box => box.role === "node");
  labels.forEach(label => nodes.forEach(node => {
    if (rectsOverlap(label.rect, rects[node.id])) problems.push({ id: label.id, problem: `标签压在节点 ${node.id} 上` });
  }));
  return problems;
}
