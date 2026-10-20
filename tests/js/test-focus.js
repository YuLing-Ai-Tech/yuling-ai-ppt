// region ⊃ vpc ⊃ { api, db }；web 在外面；cdn 只和 web 相连
const GRAPH = {
  parents: { region: null, vpc: "region", api: "vpc", db: "vpc", web: null, cdn: null },
  edges: [
    { id: "web→api", from: "web", to: "api" },
    { id: "api→db", from: "api", to: "db" },
    { id: "cdn→web", from: "cdn", to: "web" },
  ],
};

test("点节点：留它、1 层内相连的节点和连线，以及这些节点的祖先容器", () => {
  assertEqual(focusKeepSet(GRAPH, ["web"], 1), { boxes: ["api", "cdn", "region", "vpc", "web"], edges: ["cdn→web", "web→api"] });
});

test("数字键 2：再往外一层", () => {
  assertEqual(focusKeepSet(GRAPH, ["cdn"], 2), { boxes: ["api", "cdn", "region", "vpc", "web"], edges: ["cdn→web", "web→api"] });
  assertEqual(focusKeepSet(GRAPH, ["cdn"], 1), { boxes: ["cdn", "web"], edges: ["cdn→web"] });
});

test("点容器：容器里的全部子孙都算它本身", () => {
  assertEqual(focusKeepSet(GRAPH, ["vpc"], 1), { boxes: ["api", "db", "region", "vpc", "web"], edges: ["api→db", "web→api"] });
});

test("高亮路径：只留这串节点和相邻两个之间的连线，方向不限", () => {
  assertEqual(routeKeepSet(GRAPH, ["db", "api", "web"]), { boxes: ["api", "db", "region", "vpc", "web"], edges: ["api→db", "web→api"] });
});
