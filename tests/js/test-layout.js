const CELL = { width: 10, height: 20 };

test("parseGridBox 读 4 个数，允许小数", () => {
  assertEqual(parseGridBox(" 1 2.5  3 4 "), { column: 1, row: 2.5, width: 3, height: 4 });
});

test("parseGridBox 个数不对或不是数字返回 null", () => {
  assertEqual([parseGridBox("1 2 3"), parseGridBox("1 2 x 4"), parseGridBox(undefined)], [null, null, null]);
});

test("顶层盒子按网格换算像素", () => {
  const { rects, depths } = layoutBoxes([{ id: "a", parent: null, at: { column: 1, row: 2, width: 3, height: 1 } }], CELL);
  assertEqual(rects.a, { x: 10, y: 40, w: 30, h: 20 });
  assertEqual(depths.a, 0);
});

test("data-in 坐标相对父容器，多层嵌套逐层累加，子先写父后写也行", () => {
  const { rects, depths, problems } = layoutBoxes([
    { id: "node", parent: "subnet", at: { column: 0.5, row: 1, width: 2, height: 1 } },
    { id: "subnet", parent: "vpc", at: { column: 1, row: 1, width: 5, height: 3 } },
    { id: "vpc", parent: null, at: { column: 2, row: 1, width: 10, height: 6 } },
  ], CELL);
  assertEqual(rects.node, { x: 35, y: 60, w: 20, h: 20 });
  assertEqual([depths.vpc, depths.subnet, depths.node], [0, 1, 2]);
  assertEqual(problems, []);
});

test("挪动父容器，子孙跟着走", () => {
  const boxes = column => [
    { id: "vpc", parent: null, at: { column, row: 0, width: 10, height: 6 } },
    { id: "api", parent: "vpc", at: { column: 1, row: 1, width: 2, height: 1 } },
  ];
  assertEqual(layoutBoxes(boxes(5), CELL).rects.api.x - layoutBoxes(boxes(2), CELL).rects.api.x, 30);
});

test("父容器不存在、成环、id 重复都报问题", () => {
  const { rects, problems } = layoutBoxes([
    { id: "lost", parent: "nowhere", at: { column: 0, row: 0, width: 1, height: 1 } },
    { id: "a", parent: "b", at: { column: 0, row: 0, width: 1, height: 1 } },
    { id: "b", parent: "a", at: { column: 0, row: 0, width: 1, height: 1 } },
    { id: "twin", parent: null, at: { column: 0, row: 0, width: 1, height: 1 } },
    { id: "twin", parent: null, at: { column: 2, row: 0, width: 1, height: 1 } },
  ], CELL);
  assertEqual(problems, [
    { id: "twin", problem: "data-id 重复" },
    { id: "lost", problem: "父容器 nowhere 不存在" },
    { id: "a", problem: "父容器成环：a → b → a" },
  ]);
  assertEqual([rects.lost, rects.a, rects.b], [undefined, undefined, undefined]);
});

test("rectsOverlap 只碰边不算重叠", () => {
  const a = { x: 0, y: 0, w: 10, h: 10 };
  assertEqual([rectsOverlap(a, { x: 10, y: 0, w: 5, h: 5 }), rectsOverlap(a, { x: 9, y: 9, w: 5, h: 5 })], [false, true]);
});

test("rectInside 允许半像素误差", () => {
  const outer = { x: 0, y: 0, w: 100, h: 50 };
  assertEqual([rectInside({ x: -0.4, y: 0, w: 100, h: 50 }, outer), rectInside({ x: 90, y: 0, w: 11, h: 10 }, outer)], [true, false]);
});

test("rectsOverlap 竖直方向：x 重叠但 y 分开不算，y 上下碰边不算，y 真重叠才算", () => {
  const a = { x: 0, y: 0, w: 10, h: 10 };
  assertEqual([
    rectsOverlap(a, { x: 0, y: 20, w: 10, h: 5 }),
    rectsOverlap(a, { x: 0, y: 10, w: 10, h: 5 }),
    rectsOverlap(a, { x: 0, y: -5, w: 10, h: 5 }),
    rectsOverlap(a, { x: 0, y: 9, w: 10, h: 5 }),
  ], [false, false, false, true]);
});

test("rectInside 竖直方向：上沿越界、下沿越界都不算在内，半像素内算", () => {
  const outer = { x: 0, y: 0, w: 100, h: 50 };
  assertEqual([
    rectInside({ x: 0, y: -5, w: 10, h: 10 }, outer),
    rectInside({ x: 0, y: 45, w: 10, h: 10 }, outer),
    rectInside({ x: 0, y: -0.4, w: 10, h: 50.8 }, outer),
  ], [false, false, true]);
});
