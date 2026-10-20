const CANVAS = { x: 0, y: 0, w: 1000, h: 600 };
const RECTS = {
  vpc: { x: 100, y: 100, w: 400, h: 300 },
  api: { x: 120, y: 120, w: 100, h: 60 },
  db: { x: 300, y: 120, w: 100, h: 60 },
  web: { x: 700, y: 120, w: 100, h: 60 },
};
const BOXES = [
  { id: "vpc", parent: null, role: "container" },
  { id: "api", parent: "vpc", role: "node" },
  { id: "db", parent: "vpc", role: "node" },
  { id: "web", parent: null, role: "node" },
];
const cleanDiagram = () => ({ boxes: BOXES.map(box => ({ ...box })), rects: JSON.parse(JSON.stringify(RECTS)), canvas: CANVAS,
  edges: [{ id: "web→api", from: "web", to: "api" }, { id: "api→vpc", from: "api", to: "vpc" }],
  labels: [{ id: "web→api 的标签", rect: { x: 560, y: 140, w: 60, h: 20 } }] });

test("干净的图没有问题；连线可以连容器", () => {
  assertEqual(findDiagramProblems(cleanDiagram()), []);
});

test("连线端点不存在", () => {
  const diagram = cleanDiagram();
  diagram.edges.push({ id: "web→ghost", from: "web", to: "ghost" });
  assertEqual(findDiagramProblems(diagram), [{ id: "web→ghost", problem: "连线端点 ghost 不存在" }]);
});

test("同一容器里的节点重叠；不同容器的不算", () => {
  const diagram = cleanDiagram();
  diagram.rects.db.x = 200;
  diagram.rects.web = { x: 150, y: 450, w: 100, h: 60 };
  assertEqual(findDiagramProblems(diagram), [{ id: "api × db", problem: "同一容器里重叠" }]);
});

test("节点超出父容器；顶层超出图区", () => {
  const diagram = cleanDiagram();
  diagram.rects.db.x = 450;
  diagram.rects.web.x = 950;
  assertEqual(findDiagramProblems(diagram), [{ id: "db", problem: "超出父容器 vpc" }, { id: "web", problem: "超出图区" }]);
});

test("标签压在节点上", () => {
  const diagram = cleanDiagram();
  diagram.labels[0].rect.x = 680;
  assertEqual(findDiagramProblems(diagram), [{ id: "web→api 的标签", problem: "标签压在节点 web 上" }]);
});

test("decor（图例、时间轴）只查出界，不查重叠", () => {
  const diagram = cleanDiagram();
  diagram.boxes.push({ id: "axis", parent: null, role: "decor" });
  diagram.rects.axis = { x: 650, y: 100, w: 300, h: 100 };
  assertEqual(findDiagramProblems(diagram), []);
});

test("decor 出界照样报", () => {
  const diagram = cleanDiagram();
  diagram.boxes.push({ id: "axis", parent: null, role: "decor" });
  diagram.rects.axis = { x: 800, y: 100, w: 300, h: 100 };
  assertEqual(findDiagramProblems(diagram), [{ id: "axis", problem: "超出图区" }]);
});

test("边界：节点紧挨（间距 0）不算重叠，多压 1 像素才算", () => {
  const diagram = cleanDiagram();
  diagram.rects.db.x = 220;
  assertEqual(findDiagramProblems(diagram), []);
  diagram.rects.db.x = 219;
  assertEqual(findDiagramProblems(diagram), [{ id: "api × db", problem: "同一容器里重叠" }]);
});

test("边界：节点恰好贴着父容器和图区的边不算出界，越过 1 像素才算", () => {
  const diagram = cleanDiagram();
  diagram.rects.db.x = 400;
  diagram.rects.web.x = 900;
  assertEqual(findDiagramProblems(diagram), []);
  diagram.rects.db.x = 401;
  diagram.rects.web.x = 901;
  assertEqual(findDiagramProblems(diagram), [{ id: "db", problem: "超出父容器 vpc" }, { id: "web", problem: "超出图区" }]);
});

test("边界：标签边贴着节点边不算压住，越过 1 像素才算", () => {
  const diagram = cleanDiagram();
  diagram.labels[0].rect.x = 640;
  assertEqual(findDiagramProblems(diagram), []);
  diagram.labels[0].rect.x = 800;
  assertEqual(findDiagramProblems(diagram), []);
  diagram.labels[0].rect.x = 641;
  assertEqual(findDiagramProblems(diagram), [{ id: "web→api 的标签", problem: "标签压在节点 web 上" }]);
});

test("标签压在容器上不算，只查节点", () => {
  const diagram = cleanDiagram();
  diagram.labels[0].rect = { x: 250, y: 300, w: 60, h: 20 };
  assertEqual(findDiagramProblems(diagram), []);
});

// 坐标系：layoutBoxes 的 rects 是图区绝对像素（子节点已叠加父容器原点），parseVias 的拐点是「网格 × 每格像素」，
// 同样从图区原点起算、不随父容器移动；canvas 原点是 (0,0)。三者同一坐标系，标签才能直接和 rects 比。
test("坐标系：嵌套节点旁的 via 拐点标签，rects、canvas、via 同一坐标系", () => {
  const cell = { width: 100, height: 50 };
  const { rects } = layoutBoxes([
    { id: "src", parent: null, at: { column: 0, row: 2, width: 1, height: 1 } },
    { id: "dst", parent: null, at: { column: 8, row: 8, width: 1, height: 1 } },
    { id: "grp", parent: null, at: { column: 5, row: 2, width: 4, height: 4 } },
    { id: "obs", parent: "grp", at: { column: 1, row: 2, width: 1, height: 1 } },
  ], cell);
  assertEqual(rects.obs, { x: 600, y: 200, w: 100, h: 50 });
  const route = routeEdge({ start: anchorPoint(rects.src, "r", 0), startSide: "r", end: anchorPoint(rects.dst, "t", 0), endSide: "t",
    vias: parseVias("6,4", cell), endOffset: 0, route: "ortho" });
  assertEqual(route.points, [{ x: 100, y: 125 }, { x: 600, y: 125 }, { x: 600, y: 200 }, { x: 850, y: 200 }, { x: 850, y: 400 }]);
  const cornerLabel = { id: "转角标签", rect: { x: 580, y: 190, w: 40, h: 20 } };
  const diagram = {
    boxes: [{ id: "src", parent: null, role: "node" }, { id: "dst", parent: null, role: "node" },
      { id: "grp", parent: null, role: "container" }, { id: "obs", parent: "grp", role: "node" }],
    rects, canvas: CANVAS, edges: [{ id: "src→dst", from: "src", to: "dst" }], labels: [cornerLabel],
  };
  assertEqual(findDiagramProblems(diagram), [{ id: "转角标签", problem: "标签压在节点 obs 上" }]);
  // 保护力在上面对 rects.obs 与 route.points 的断言：若 parseVias 叠加了父容器原点，转角就不是 (600,200)，这里会红
});

test("连线起点 from 不存在；两端都不存在报两条", () => {
  const diagram = cleanDiagram();
  diagram.edges.push({ id: "ghost→web", from: "ghost", to: "web" }, { id: "g1→g2", from: "g1", to: "g2" });
  assertEqual(findDiagramProblems(diagram), [{ id: "ghost→web", problem: "连线端点 ghost 不存在" },
    { id: "g1→g2", problem: "连线端点 g1 不存在" }, { id: "g1→g2", problem: "连线端点 g2 不存在" }]);
});

test("同一容器三个节点：首尾重叠、中间不重叠，也要报", () => {
  const diagram = cleanDiagram();
  diagram.boxes.push({ id: "cache", parent: "vpc", role: "node" });
  diagram.rects.api = { x: 120, y: 120, w: 100, h: 60 };
  diagram.rects.db = { x: 120, y: 300, w: 100, h: 60 };
  diagram.rects.cache = { x: 180, y: 140, w: 100, h: 60 };
  assertEqual(findDiagramProblems(diagram), [{ id: "api × cache", problem: "同一容器里重叠" }]);
});

test("容器套容器：节点按直接父容器查，超出直接父容器但仍在祖父里也要报", () => {
  const boxes = [{ id: "outer", parent: null, role: "container" }, { id: "inner", parent: "outer", role: "container" },
    { id: "leaf", parent: "inner", role: "node" }];
  const rects = { outer: { x: 0, y: 0, w: 600, h: 400 }, inner: { x: 100, y: 100, w: 200, h: 150 }, leaf: { x: 250, y: 120, w: 100, h: 50 } };
  assertEqual(findDiagramProblems({ boxes, rects, canvas: CANVAS, edges: [], labels: [] }), [{ id: "leaf", problem: "超出父容器 inner" }]);
  rects.leaf.x = 200;
  assertEqual(findDiagramProblems({ boxes, rects, canvas: CANVAS, edges: [], labels: [] }), []);
});

// 父容器没有 rect 时不查出界（不重复报）。layoutBoxes 保证子节点的 rect 只在父容器有 rect 时才产生，
// 所以真实链路里"父在子无"不会出现；父容器缺失/成环由 layoutBoxes 自己报，子节点一并没有 rect，被 placed 过滤掉
test("父容器没有 rect：不报出界，问题由 layoutBoxes 报", () => {
  const { rects, problems } = layoutBoxes([{ id: "orphan", parent: "missing", at: { column: 0, row: 0, width: 1, height: 1 } }], { width: 100, height: 50 });
  assertEqual(rects, {});
  assertEqual(problems, [{ id: "orphan", problem: "父容器 missing 不存在" }]);
  assertEqual(findDiagramProblems({ boxes: [{ id: "orphan", parent: "missing", role: "node" }], rects, canvas: CANVAS, edges: [], labels: [] }), []);
  assertEqual(findDiagramProblems({ boxes: [{ id: "kid", parent: "missing", role: "node" }], rects: { kid: { x: 5000, y: 0, w: 10, h: 10 } },
    canvas: CANVAS, edges: [], labels: [] }), []);
});
