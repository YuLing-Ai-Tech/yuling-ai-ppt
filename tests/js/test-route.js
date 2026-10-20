const box = (x, y, w, h) => ({ x, y, w, h });

test("parseEndpoint 拆出 id 和边，不认识的边当作没写", () => {
  assertEqual([parseEndpoint("db:t"), parseEndpoint("api"), parseEndpoint("api:x")],
    [{ id: "db", side: "t" }, { id: "api", side: null }, { id: "api", side: null }]);
});

test("parseVias 把网格拐点换成像素", () => {
  assertEqual(parseVias("1,2  3.5,0", { width: 10, height: 20 }), [{ x: 10, y: 40 }, { x: 35, y: 0 }]);
});

test("autoSides：上下有重叠走左右边，左右有重叠走上下边", () => {
  assertEqual(autoSides(box(0, 0, 100, 50), box(300, 20, 100, 50)), ["r", "l"]);
  assertEqual(autoSides(box(300, 20, 100, 50), box(0, 0, 100, 50)), ["l", "r"]);
  assertEqual(autoSides(box(0, 0, 100, 50), box(20, 200, 100, 50)), ["b", "t"]);
  assertEqual(autoSides(box(20, 200, 100, 50), box(0, 0, 100, 50)), ["t", "b"]);
});

test("autoSides：都不重叠时看哪个方向离得远", () => {
  assertEqual(autoSides(box(0, 0, 50, 50), box(400, 100, 50, 50)), ["r", "l"]);
  assertEqual(autoSides(box(0, 0, 50, 50), box(100, 400, 50, 50)), ["b", "t"]);
});

test("portOffsets：同一条边上的线按对端位置错开，单根线不偏", () => {
  const offsets = portOffsets([
    { key: "gw:r", otherCenter: { x: 500, y: 300 } },
    { key: "gw:r", otherCenter: { x: 500, y: 100 } },
    { key: "gw:r", otherCenter: { x: 500, y: 200 } },
    { key: "db:t", otherCenter: { x: 0, y: 0 } },
  ]);
  assertEqual(offsets, [24, -24, 0, 0]);
});

test("anchorPoint 四条边的中点加偏移", () => {
  const rect = box(100, 100, 40, 20);
  assertEqual(["r", "l", "t", "b"].map(side => anchorPoint(rect, side, 5)),
    [{ x: 140, y: 115 }, { x: 100, y: 115 }, { x: 125, y: 100 }, { x: 125, y: 120 }]);
});

test("simplifyPoints 去掉重合点和共线中间点", () => {
  assertEqual(simplifyPoints([{ x: 0, y: 0 }, { x: 0, y: 0 }, { x: 5, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }]),
    [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }]);
});

test("routeOrthogonal：左右边对左右边走 Z 形，中段在两端正中", () => {
  assertEqual(routeOrthogonal({ x: 0, y: 0 }, "r", { x: 100, y: 50 }, "l", [], 0),
    [{ x: 0, y: 0 }, { x: 50, y: 0 }, { x: 50, y: 50 }, { x: 100, y: 50 }]);
});

test("routeOrthogonal：左右边对上下边走 L 形；对齐时直连", () => {
  assertEqual(routeOrthogonal({ x: 0, y: 0 }, "r", { x: 100, y: 50 }, "t", [], 0),
    [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 50 }]);
  assertEqual(routeOrthogonal({ x: 0, y: 10 }, "r", { x: 100, y: 10 }, "l", [], 0), [{ x: 0, y: 10 }, { x: 100, y: 10 }]);
});

test("routeOrthogonal：经过 data-via 拐点，横竖交替", () => {
  assertEqual(routeOrthogonal({ x: 0, y: 0 }, "b", { x: 100, y: 0 }, "b", [{ x: 50, y: 80 }], 0),
    [{ x: 0, y: 0 }, { x: 0, y: 80 }, { x: 100, y: 80 }, { x: 100, y: 0 }]);
});

test("roundedPathData 拐角用二次曲线收圆，半径不超过相邻段的一半", () => {
  assertEqual(roundedPathData([{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 100 }]), "M 0 0 L 5 0 Q 10 0 10 5 L 10 100");
});

// 把路径串还原成折点，检查每一段（Q 取起点到控制点、控制点到终点）都沿横轴或纵轴
function pathSegmentsAreAxisAligned(pathData) {
  const tokens = pathData.match(/[MLQ]|-?[\d.]+(?:e-?\d+)?/g);
  const segments = [];
  let current = null;
  for (let index = 0; index < tokens.length;) {
    const command = tokens[index++];
    const pointCount = command === "Q" ? 2 : 1;
    for (let count = 0; count < pointCount; count++) {
      const point = { x: Number(tokens[index++]), y: Number(tokens[index++]) };
      if (command !== "M") segments.push([current, point]);
      current = point;
    }
  }
  return segments.every(([from, to]) => Math.abs(from.x - to.x) < 1e-6 || Math.abs(from.y - to.y) < 1e-6);
}

test("roundedPathData：via 与终点的 y 只差浮点误差时，每一段仍沿横轴或纵轴", () => {
  const route = routeEdge({ start: { x: 0, y: 0 }, startSide: "r", end: { x: 200, y: 50 }, endSide: "l",
    vias: [{ x: 100, y: 50 + 1e-13 }], endOffset: 0, route: "ortho" });
  assertEqual(pathSegmentsAreAxisAligned(route.pathData), true);
});

test("roundedPathData：via 与终点的 x 只差浮点误差时，每一段仍沿横轴或纵轴", () => {
  const route = routeEdge({ start: { x: 0, y: 0 }, startSide: "b", end: { x: 50, y: 200 }, endSide: "t",
    vias: [{ x: 50 + 1e-13, y: 100 }], endOffset: 0, route: "ortho" });
  assertEqual(pathSegmentsAreAxisAligned(route.pathData), true);
});

test("routeEdge 直线：两点一段，标签在正中", () => {
  const route = routeEdge({ start: { x: 0, y: 0 }, startSide: "r", end: { x: 100, y: 40 }, endSide: "l", vias: [], endOffset: 0, route: "straight" });
  assertEqual([route.pathData, route.labelAt], ["M 0 0 L 100 40", { x: 50, y: 20 }]);
});

test("routeEdge 曲线：控制点沿出口方向伸出，标签在 t=0.5", () => {
  const route = routeEdge({ start: { x: 0, y: 0 }, startSide: "r", end: { x: 200, y: 0 }, endSide: "l", vias: [], endOffset: 0, route: "curve" });
  assertEqual(route.pathData, "M 0 0 C 100 0 100 0 200 0");
  assertEqual([route.labelAt, route.points.length], [{ x: 100, y: 0 }, 17]);
});

test("routeEdge 正交：标签放在最长那段的中点", () => {
  const route = routeEdge({ start: { x: 0, y: 0 }, startSide: "r", end: { x: 40, y: 200 }, endSide: "t", vias: [], endOffset: 0, route: "ortho" });
  assertEqual(route.labelAt, { x: 40, y: 100 });
});

test("segmentHitsRect：穿过、碰边算相交，擦肩不算", () => {
  const rect = box(10, 10, 10, 10);
  assertEqual([segmentHitsRect({ x: 0, y: 15 }, { x: 30, y: 15 }, rect), segmentHitsRect({ x: 0, y: 10 }, { x: 30, y: 10 }, rect),
    segmentHitsRect({ x: 0, y: 25 }, { x: 30, y: 25 }, rect), segmentHitsRect({ x: 0, y: 0 }, { x: 30, y: 30 }, rect)], [true, true, false, true]);
});

test("chooseTabSide：上边被线穿过就放下边；上下都穿过仍放上边", () => {
  const top = box(20, -14, 80, 28), bottom = box(20, 186, 80, 28);
  const throughTop = [{ x: 50, y: 100 }, { x: 50, y: -100 }];
  const throughBoth = [{ x: 50, y: 300 }, { x: 50, y: -100 }];
  assertEqual([chooseTabSide(top, bottom, []), chooseTabSide(top, bottom, [throughTop]), chooseTabSide(top, bottom, [throughBoth])],
    ["top", "bottom", "top"]);
});

test("autoSides：y 有重叠时即使纵向更远也走左右边（重叠规则压过距离规则）", () => {
  assertEqual(autoSides(box(0, 0, 100, 300), box(110, 250, 100, 100)), ["r", "l"]);
});

test("autoSides：x 有重叠时即使横向更远也走上下边", () => {
  assertEqual(autoSides(box(0, 0, 100, 50), box(90, 60, 300, 50)), ["b", "t"]);
});

test("autoSides：都不重叠且横纵距离恰好相等，归左右边", () => {
  assertEqual(autoSides(box(0, 0, 50, 50), box(100, 100, 50, 50)), ["r", "l"]);
});

test("portOffsets：上下边上的线按对端 x 排序错开", () => {
  assertEqual(portOffsets([
    { key: "db:t", otherCenter: { x: 300, y: 0 } },
    { key: "db:t", otherCenter: { x: 100, y: 0 } },
    { key: "db:t", otherCenter: { x: 200, y: 0 } },
  ]), [24, -24, 0]);
});

test("routeOrthogonal：endOffset 让横向 Z 的中段偏移 0.6 倍", () => {
  assertEqual(routeOrthogonal({ x: 0, y: 0 }, "r", { x: 100, y: 50 }, "l", [], 10),
    [{ x: 0, y: 0 }, { x: 56, y: 0 }, { x: 56, y: 50 }, { x: 100, y: 50 }]);
});

test("routeOrthogonal：上下边对上下边走纵向 Z，中段在两端正中，endOffset 同样错开", () => {
  assertEqual(routeOrthogonal({ x: 0, y: 0 }, "b", { x: 50, y: 100 }, "t", [], 0),
    [{ x: 0, y: 0 }, { x: 0, y: 50 }, { x: 50, y: 50 }, { x: 50, y: 100 }]);
  assertEqual(routeOrthogonal({ x: 0, y: 0 }, "b", { x: 50, y: 100 }, "t", [], 10),
    [{ x: 0, y: 0 }, { x: 0, y: 56 }, { x: 50, y: 56 }, { x: 50, y: 100 }]);
});

test("routeOrthogonal：三个 data-via 阶梯，横竖逐个交替，共线点合并", () => {
  assertEqual(routeOrthogonal({ x: 0, y: 0 }, "r", { x: 400, y: 150 }, "l",
    [{ x: 100, y: 50 }, { x: 200, y: 100 }, { x: 300, y: 150 }], 0),
  [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 300, y: 100 }, { x: 300, y: 150 }, { x: 400, y: 150 }]);
});

test("routeEdge 曲线：两端很近时控制点至少伸出 40", () => {
  const route = routeEdge({ start: { x: 0, y: 0 }, startSide: "r", end: { x: 20, y: 0 }, endSide: "l", vias: [], endOffset: 0, route: "curve" });
  assertEqual(route.pathData, "M 0 0 C 40 0 -20 0 20 0");
});

test("segmentHitsRect：整段在矩形一侧、方向朝矩形但够不着，不相交", () => {
  const rect = box(10, 10, 10, 10);
  assertEqual([segmentHitsRect({ x: 0, y: 15 }, { x: 5, y: 15 }, rect), segmentHitsRect({ x: 30, y: 15 }, { x: 25, y: 15 }, rect),
    segmentHitsRect({ x: 15, y: 0 }, { x: 15, y: 5 }, rect)], [false, false, false]);
});

test("chooseTabSide：够不着标签的短线不算穿过；沿标签边擦过算穿过，擦肩不算", () => {
  const top = box(20, -14, 80, 28), bottom = box(20, 186, 80, 28);
  const tooShort = [{ x: 50, y: 100 }, { x: 50, y: 50 }];
  const alongTopEdge = [{ x: 0, y: -14 }, { x: 200, y: -14 }];
  const justAboveTop = [{ x: 0, y: -15 }, { x: 200, y: -15 }];
  assertEqual([tooShort, alongTopEdge, justAboveTop].map(line => chooseTabSide(top, bottom, [line])), ["top", "bottom", "top"]);
});

test("端点是嵌套容器里的节点：layoutBoxes 换出绝对位置，再连到容器外的节点", () => {
  const { rects } = layoutBoxes([
    { id: "vpc", parent: null, at: { column: 1, row: 1, width: 10, height: 6 } },
    { id: "api", parent: "vpc", at: { column: 1, row: 1, width: 2, height: 1 } },
    { id: "db", parent: null, at: { column: 14, row: 3, width: 2, height: 1 } },
  ], { width: 10, height: 20 });
  assertEqual([rects.api, rects.db], [box(20, 40, 20, 20), box(140, 60, 20, 20)]);
  const [fromSide, toSide] = autoSides(rects.api, rects.db);
  const route = routeEdge({ start: anchorPoint(rects.api, fromSide, 0), startSide: fromSide,
    end: anchorPoint(rects.db, toSide, 0), endSide: toSide, vias: [], endOffset: 0, route: "ortho" });
  assertEqual([fromSide, toSide, route.points],
    ["r", "l", [{ x: 40, y: 50 }, { x: 90, y: 50 }, { x: 90, y: 70 }, { x: 140, y: 70 }]]);
});
