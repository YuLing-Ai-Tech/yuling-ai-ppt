// 图元 · 走线（设计 §4.1）：自动选边、端口错开、正交 / 直线 / 曲线路径、线上标签位置、标签页避让。纯函数，不碰 DOM
const DIAGRAM_PORT_GAP = 24;
const DIAGRAM_CORNER_RADIUS = 12;
const DIAGRAM_CURVE_SAMPLES = 16;
const SIDE_VECTORS = { l: { x: -1, y: 0 }, r: { x: 1, y: 0 }, t: { x: 0, y: -1 }, b: { x: 0, y: 1 } };

// "db:t" → { id: "db", side: "t" }；不写边 side 为 null，交给 autoSides
function parseEndpoint(text) {
  const [id, side] = String(text || "").split(":");
  return { id, side: SIDE_VECTORS[side] ? side : null };
}

// data-via="列,行 列,行"：拐点用图区网格坐标（不随父容器移动），换算成像素
function parseVias(text, cell) {
  return String(text || "").split(/\s+/).filter(Boolean)
    .map(pair => pair.split(",").map(Number))
    .map(([column, row]) => ({ x: column * cell.width, y: row * cell.height }));
}

const rectCenter = rect => ({ x: rect.x + rect.w / 2, y: rect.y + rect.h / 2 });
const isHorizontalSide = side => side === "l" || side === "r";

// 横向错开（上下有重叠）就走左右边，纵向错开就走上下边，都不重叠时看哪个方向离得远
function autoSides(fromRect, toRect) {
  const overlapX = fromRect.x < toRect.x + toRect.w && toRect.x < fromRect.x + fromRect.w;
  const overlapY = fromRect.y < toRect.y + toRect.h && toRect.y < fromRect.y + fromRect.h;
  const from = rectCenter(fromRect), to = rectCenter(toRect);
  const dx = to.x - from.x, dy = to.y - from.y;
  const horizontal = overlapY || (!overlapX && Math.abs(dx) >= Math.abs(dy));
  if (horizontal) return dx > 0 ? ["r", "l"] : ["l", "r"];
  return dy > 0 ? ["b", "t"] : ["t", "b"];
}

// ends：[{ key: "节点id:边", otherCenter: { x, y } }]。同一条边上的几根线按对端位置排开，间距 DIAGRAM_PORT_GAP，返回同序偏移量
function portOffsets(ends) {
  const groups = new Map();
  ends.forEach((end, index) => {
    if (!groups.has(end.key)) groups.set(end.key, []);
    groups.get(end.key).push(index);
  });
  const offsets = ends.map(() => 0);
  groups.forEach(indexes => {
    const alongY = /:[lr]$/.test(ends[indexes[0]].key);
    indexes.sort((a, b) => alongY ? ends[a].otherCenter.y - ends[b].otherCenter.y : ends[a].otherCenter.x - ends[b].otherCenter.x);
    indexes.forEach((endIndex, order) => { offsets[endIndex] = (order - (indexes.length - 1) / 2) * DIAGRAM_PORT_GAP; });
  });
  return offsets;
}

function anchorPoint(rect, side, offset) {
  if (side === "r") return { x: rect.x + rect.w, y: rect.y + rect.h / 2 + offset };
  if (side === "l") return { x: rect.x, y: rect.y + rect.h / 2 + offset };
  if (side === "t") return { x: rect.x + rect.w / 2 + offset, y: rect.y };
  return { x: rect.x + rect.w / 2 + offset, y: rect.y + rect.h };
}

// 去掉重合点和共线的中间点
function simplifyPoints(points) {
  const unique = points.filter((point, index) => index === 0 ||
    Math.abs(point.x - points[index - 1].x) > .5 || Math.abs(point.y - points[index - 1].y) > .5);
  return unique.filter((point, index) => {
    if (index === 0 || index === unique.length - 1) return true;
    const before = unique[index - 1], after = unique[index + 1];
    const sameX = Math.abs(before.x - point.x) < .5 && Math.abs(point.x - after.x) < .5;
    const sameY = Math.abs(before.y - point.y) < .5 && Math.abs(point.y - after.y) < .5;
    return !(sameX || sameY);
  });
}

// 正交走线：先沿出口方向走，经过每个拐点时横竖交替，最后沿入口方向进入。endOffset 让汇到同一边的线在中段错开
function routeOrthogonal(start, startSide, end, endSide, vias, endOffset) {
  const points = [start];
  let direction = isHorizontalSide(startSide) ? "h" : "v";
  if (!vias.length) {
    const endHorizontal = isHorizontalSide(endSide);
    if (direction === "h" && endHorizontal) {
      const middleX = (start.x + end.x) / 2 + endOffset * 0.6;
      points.push({ x: middleX, y: start.y }, { x: middleX, y: end.y });
    } else if (direction === "v" && !endHorizontal) {
      const middleY = (start.y + end.y) / 2 + endOffset * 0.6;
      points.push({ x: start.x, y: middleY }, { x: end.x, y: middleY });
    } else if (direction === "h") points.push({ x: end.x, y: start.y });
    else points.push({ x: start.x, y: end.y });
    points.push(end);
    return simplifyPoints(points);
  }
  vias.forEach(via => {
    const last = points[points.length - 1];
    points.push(direction === "h" ? { x: via.x, y: last.y } : { x: last.x, y: via.y }, via);
    direction = direction === "h" ? "v" : "h";
  });
  const last = points[points.length - 1];
  points.push(isHorizontalSide(endSide) ? { x: last.x, y: end.y } : { x: end.x, y: last.y }, end);
  return simplifyPoints(points);
}

// 差不足 0.5 像素视为同轴（与 simplifyPoints 同口径），避免浮点误差的符号把圆角起止点推歪
function axisSign(delta) {
  return Math.abs(delta) < .5 ? 0 : Math.sign(delta);
}

function roundedPathData(points) {
  let pathData = `M ${points[0].x} ${points[0].y}`;
  for (let index = 1; index < points.length - 1; index++) {
    const before = points[index - 1], corner = points[index], after = points[index + 1];
    const radius = Math.min(DIAGRAM_CORNER_RADIUS, Math.hypot(corner.x - before.x, corner.y - before.y) / 2,
      Math.hypot(after.x - corner.x, after.y - corner.y) / 2);
    const inX = axisSign(corner.x - before.x), inY = axisSign(corner.y - before.y);
    const outX = axisSign(after.x - corner.x), outY = axisSign(after.y - corner.y);
    pathData += ` L ${corner.x - inX * radius} ${corner.y - inY * radius} Q ${corner.x} ${corner.y} ${corner.x + outX * radius} ${corner.y + outY * radius}`;
  }
  const last = points[points.length - 1];
  return `${pathData} L ${last.x} ${last.y}`;
}

function longestSegmentMiddle(points) {
  let best = null, bestLength = -1;
  for (let index = 1; index < points.length; index++) {
    const length = Math.hypot(points[index].x - points[index - 1].x, points[index].y - points[index - 1].y);
    if (length > bestLength) {
      bestLength = length;
      best = { x: (points[index].x + points[index - 1].x) / 2, y: (points[index].y + points[index - 1].y) / 2 };
    }
  }
  return best;
}

function bezierPoint(p0, p1, p2, p3, t) {
  const u = 1 - t;
  const blend = axis => u * u * u * p0[axis] + 3 * u * u * t * p1[axis] + 3 * u * t * t * p2[axis] + t * t * t * p3[axis];
  return { x: blend("x"), y: blend("y") };
}

// 曲线：两端沿各自出口方向伸出控制点，伸出长度取两端距离的一半
function curveRoute(start, startSide, end, endSide) {
  const reach = Math.max(40, Math.hypot(end.x - start.x, end.y - start.y) / 2);
  const control1 = { x: start.x + SIDE_VECTORS[startSide].x * reach, y: start.y + SIDE_VECTORS[startSide].y * reach };
  const control2 = { x: end.x + SIDE_VECTORS[endSide].x * reach, y: end.y + SIDE_VECTORS[endSide].y * reach };
  const points = Array.from({ length: DIAGRAM_CURVE_SAMPLES + 1 }, (_, index) =>
    bezierPoint(start, control1, control2, end, index / DIAGRAM_CURVE_SAMPLES));
  return { pathData: `M ${start.x} ${start.y} C ${control1.x} ${control1.y} ${control2.x} ${control2.y} ${end.x} ${end.y}`,
    points, labelAt: bezierPoint(start, control1, control2, end, 0.5) };
}

// edge：{ start, startSide, end, endSide, vias, endOffset, route: "ortho"|"straight"|"curve" }
// 返回 { pathData, points, labelAt }；points 是折线（曲线取采样点），给标签页避让和连线检查用
function routeEdge(edge) {
  if (edge.route === "straight") {
    const points = [edge.start, edge.end];
    return { pathData: `M ${edge.start.x} ${edge.start.y} L ${edge.end.x} ${edge.end.y}`, points, labelAt: longestSegmentMiddle(points) };
  }
  if (edge.route === "curve") return curveRoute(edge.start, edge.startSide, edge.end, edge.endSide);
  const points = routeOrthogonal(edge.start, edge.startSide, edge.end, edge.endSide, edge.vias, edge.endOffset);
  return { pathData: roundedPathData(points), points, labelAt: longestSegmentMiddle(points) };
}

// 线段与矩形是否相交（含碰边），Liang–Barsky 裁剪
function segmentHitsRect(a, b, rect) {
  let enter = 0, leave = 1;
  const dx = b.x - a.x, dy = b.y - a.y;
  const limits = [[-dx, a.x - rect.x], [dx, rect.x + rect.w - a.x], [-dy, a.y - rect.y], [dy, rect.y + rect.h - a.y]];
  for (const [direction, distance] of limits) {
    if (direction === 0) {
      if (distance < 0) return false;
      continue;
    }
    const ratio = distance / direction;
    if (direction < 0) {
      if (ratio > leave) return false;
      enter = Math.max(enter, ratio);
    } else {
      if (ratio < enter) return false;
      leave = Math.min(leave, ratio);
    }
  }
  return true;
}

function polylineHitsRect(points, rect) {
  for (let index = 1; index < points.length; index++) if (segmentHitsRect(points[index - 1], points[index], rect)) return true;
  return false;
}

// 标签页默认在容器上边框；有线穿过就改放下边框（设计 §4.2）。上下都被穿过时仍放上边框
function chooseTabSide(topRect, bottomRect, polylines) {
  if (!polylines.some(points => polylineHitsRect(points, topRect))) return "top";
  return polylines.some(points => polylineHitsRect(points, bottomRect)) ? "top" : "bottom";
}
