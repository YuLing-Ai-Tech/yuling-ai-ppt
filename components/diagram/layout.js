// 图元 · 网格与嵌套（设计 §4.1）：data-at="列 行 宽 高" 换算成图区像素，data-in 指定父容器、坐标相对父容器。纯函数，不碰 DOM
const DIAGRAM_EDGE_TOLERANCE = 0.5;

function parseGridBox(text) {
  const numbers = String(text || "").trim().split(/\s+/).map(Number);
  if (numbers.length !== 4 || numbers.some(value => !Number.isFinite(value))) return null;
  const [column, row, width, height] = numbers;
  return { column, row, width, height };
}

// boxes：[{ id, parent, at }]，parent 为 null 表示直接在图区里；cell：{ width, height } 每格像素
// 返回 { rects: { id: { x, y, w, h } }, depths: { id: 嵌套层数 }, problems: [{ id, problem }] }
function layoutBoxes(boxes, cell) {
  const byId = new Map();
  const problems = [];
  boxes.forEach(box => {
    if (byId.has(box.id)) problems.push({ id: box.id, problem: "data-id 重复" });
    byId.set(box.id, box);
  });
  const rects = {}, depths = {}, failed = new Set();
  const resolve = (box, trail) => {
    if (rects[box.id] || failed.has(box.id)) return rects[box.id] || null;
    if (trail.includes(box.id)) {
      failed.add(box.id);
      problems.push({ id: box.id, problem: `父容器成环：${[...trail, box.id].join(" → ")}` });
      return null;
    }
    let originX = 0, originY = 0, depth = 0;
    if (box.parent) {
      const parent = byId.get(box.parent);
      if (!parent) {
        failed.add(box.id);
        problems.push({ id: box.id, problem: `父容器 ${box.parent} 不存在` });
        return null;
      }
      const parentRect = resolve(parent, [...trail, box.id]);
      if (!parentRect) { failed.add(box.id); return null; }
      originX = parentRect.x; originY = parentRect.y; depth = depths[parent.id] + 1;
    }
    depths[box.id] = depth;
    rects[box.id] = { x: originX + box.at.column * cell.width, y: originY + box.at.row * cell.height,
      w: box.at.width * cell.width, h: box.at.height * cell.height };
    return rects[box.id];
  };
  boxes.forEach(box => resolve(box, []));
  return { rects, depths, problems };
}

// 两个矩形有正面积的重叠（只碰边不算）
function rectsOverlap(a, b) {
  const gap = DIAGRAM_EDGE_TOLERANCE;
  return a.x < b.x + b.w - gap && b.x < a.x + a.w - gap && a.y < b.y + b.h - gap && b.y < a.y + a.h - gap;
}

function rectInside(inner, outer) {
  const gap = DIAGRAM_EDGE_TOLERANCE;
  return inner.x >= outer.x - gap && inner.y >= outer.y - gap &&
    inner.x + inner.w <= outer.x + outer.w + gap && inner.y + inner.h <= outer.y + outer.h + gap;
}
