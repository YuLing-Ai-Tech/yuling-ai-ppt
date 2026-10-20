// 树布局纯函数：坐标单位是网格，从 0 起、未居中；节点默认 4×1.4，层距 1.5、兄弟距 0.5
const SIZE = { w: 4, h: 1.4 };
const GAP = { level: 1.5, sibling: 0.5 };
const tree = (...pairs) => pairs.map(([id, parent, side]) => ({ id, parent: parent || null, side: side || null, size: SIZE }));
const at = (column, row) => ({ column, row, width: 4, height: 1.4 });

test("上下：父节点居中在子树上方，叶子按兄弟距排开，连线从父的下边到子的上边", () => {
  const result = layoutTree(tree(["root"], ["a", "root"], ["b", "root"]), "down", GAP);
  assertEqual(result.boxes, { root: at(2.25, 0), a: at(0, 2.9), b: at(4.5, 2.9) });
  assertEqual(result.edges, [{ from: "root", to: "a", fromSide: "b", toSide: "t" }, { from: "root", to: "b", fromSide: "b", toSide: "t" }]);
  assertEqual([result.extent, result.problems], [{ columns: 8.5, rows: 4.3 }, []]);
});

test("上下：子树宽的兄弟占得多，父节点居中在首末孩子中心的中点；父节点比子树宽时子树在父节点下居中", () => {
  const result = layoutTree(tree(["r"], ["a", "r"], ["a1", "a"], ["a2", "a"], ["b", "r"]), "down", GAP);
  assertEqual(result.boxes.a, at(2.25, 2.9));
  assertEqual(result.boxes.b, at(9, 2.9));
  assertEqual(result.boxes.r, at(5.625, 0));  // 居中在 a、b 两个孩子中心（4.25、11）的中点 7.625
  const single = layoutTree([{ id: "r", parent: null, size: { w: 10, h: 1.4 } }, { id: "c", parent: "r", size: SIZE }], "down", GAP);
  assertEqual(single.boxes.c, at(3, 2.9));
});

test("左右（知识结构图）：深度沿横轴，连线从父的右边到子的左边", () => {
  const result = layoutTree(tree(["root"], ["a", "root"], ["b", "root"]), "right", GAP);
  assertEqual(result.boxes, { root: at(0, 0.95), a: at(5.5, 0), b: at(5.5, 1.9) });
  assertEqual(result.edges.map(edge => edge.fromSide + edge.toSide), ["rl", "rl"]);
});

test("思维导图：根的孩子前一半放右边、后一半放左边，data-side 可指定；左边镜像", () => {
  const result = layoutTree(tree(["root"], ["a", "root"], ["b", "root"], ["c", "root"], ["d", "root", "r"]), "mind", GAP);
  // 右边 a、b、d（d 指定 r），左边 c；左边在根左侧，右对齐到层距
  assertEqual(result.boxes.root, at(5.5, 1.9));
  assertEqual([result.boxes.a, result.boxes.b, result.boxes.d], [at(11, 0), at(11, 1.9), at(11, 3.8)]);
  assertEqual(result.boxes.c, at(0, 1.9));
  assertEqual(result.edges.map(edge => `${edge.to}:${edge.fromSide}${edge.toSide}`), ["a:rl", "b:rl", "c:lr", "d:rl"]);
});

test("坏树：没有根、多个根、父节点不存在、成环，各报一条，其余照排", () => {
  assertEqual(layoutTree(tree(["a", "b"], ["b", "a"]), "down", GAP).problems,
    [{ id: "a", problem: "不在树上（父节点成环，或没有根）" }, { id: "b", problem: "不在树上（父节点成环，或没有根）" }]);
  const broken = layoutTree(tree(["r"], ["s"], ["x", "nope"], ["c", "r"]), "down", GAP);
  assertEqual(broken.problems, [{ id: "s", problem: "树只能有一个根，已有 r" }, { id: "x", problem: "父节点 nope 不存在" }]);
  assertEqual(Object.keys(broken.boxes), ["r", "c"]);
});

// 父节点中心 = 首个子节点中心与末个子节点中心的中点（整齐树）；兄弟子树宽度悬殊时也成立，且同层节点不重叠
const LOPSIDED = tree(["r"], ["a", "r"], ["a1", "a"], ["a2", "a"], ["a3", "a"], ["a4", "a"], ["b", "r"], ["c", "r"], ["c1", "c"], ["c1x", "c1"], ["c1y", "c1"]);
const centreOf = (box, axis) => axis === "column" ? box.column + box.width / 2 : box.row + box.height / 2;

[["down", "column"], ["right", "row"], ["mind", "row"]].forEach(([direction, axis]) => {
  test(`${direction}：父节点居中在首末子节点中心的中点（兄弟子树宽度悬殊），同一父节点的兄弟不重叠`, () => {
    const nodes = LOPSIDED;
    const { boxes, problems } = layoutTree(nodes, direction, GAP);
    assertEqual(problems, []);
    const extentOf = axis === "column" ? "width" : "height";
    const centreOfNode = id => centreOf(boxes[id], axis);
    nodes.forEach(parent => {
      const kids = nodes.filter(node => node.parent === parent.id);
      if (!kids.length) return;
      // mind 的根有左右两侧，各查各的（列比根大的在右侧）
      const groups = direction === "mind" && parent.id === "r"
        ? [kids.filter(kid => boxes[kid.id].column > boxes.r.column), kids.filter(kid => boxes[kid.id].column < boxes.r.column)] : [kids];
      groups.forEach(side => {
        const mid = (centreOfNode(side[0].id) + centreOfNode(side[side.length - 1].id)) / 2;
        assertEqual(Math.abs(mid - centreOfNode(parent.id)) <= 0.1, true, `${parent.id}：首末子中点 ${mid}，父中心 ${centreOfNode(parent.id)}。`);
        const sorted = side.map(kid => boxes[kid.id]).sort((first, second) => first[axis] - second[axis]);
        sorted.slice(1).forEach((box, index) => assertEqual(box[axis] >= sorted[index][axis] + sorted[index][extentOf] + GAP.sibling - 0.001, true, `${parent.id} 的兄弟重叠。`));
      });
    });
  });
});

test("未知方向（拼错的 data-tree）：每个节点报一条问题，不排也不连线", () => {
  const result = layoutTree(tree(["r"], ["a", "r"]), "rihgt", GAP);
  const reason = "未知 data-tree 值 rihgt（只能写 down、right、mind）";
  assertEqual([result.problems, result.boxes, result.edges], [[{ id: "r", problem: reason }, { id: "a", problem: reason }], {}, []]);
});

// 节点尺寸混用（B5）：父节点比孩子块宽且两个孩子宽度不等时，父中心仍是首末子中心的中点，且全图任意两盒不相交
const sized = (width, id, parent) => ({ id, parent: parent || null, side: null, size: { w: width, h: 1 } });
const boxesOverlap = (first, second) => first.column < second.column + second.width && second.column < first.column + first.width &&
  first.row < second.row + second.height && second.row < first.row + first.height;

function assertMidpointAndNoOverlap(nodes, direction) {
  const { boxes } = layoutTree(nodes, direction, GAP);
  const centreColumn = id => boxes[id].column + boxes[id].width / 2;
  nodes.forEach(parent => {
    const kids = nodes.filter(node => node.parent === parent.id);
    if (!kids.length || direction === "mind") return;
    const mid = (centreColumn(kids[0].id) + centreColumn(kids[kids.length - 1].id)) / 2;
    assertEqual(Math.abs(mid - centreColumn(parent.id)) <= 0.01, true, `${parent.id}：首末子中点 ${mid}，父中心 ${centreColumn(parent.id)}。`);
  });
  const ids = Object.keys(boxes);
  ids.forEach((first, index) => ids.slice(index + 1).forEach(second => assertEqual(boxesOverlap(boxes[first], boxes[second]), false, `${first} 与 ${second} 重叠。`)));
}

test("上下：父节点（宽 6）的两个孩子宽 2 和 4，父中心仍在孩子中心的中点（原先被夹回占宽，偏 0.25）", () => {
  assertMidpointAndNoOverlap([sized(3, "r"), sized(6, "n1", "r"), sized(2, "n2", "n1"), sized(4, "n3", "n1")], "down");
});

test("上下：随机混用节点尺寸的树，父中心都在首末子中心的中点，任意两盒不相交", () => {
  let seed = 7;
  const random = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648;
  for (let round = 0; round < 300; round++) {
    const nodes = [sized(2 + Math.floor(random() * 4), "r")];
    const nodeCount = 2 + Math.floor(random() * 6);
    for (let index = 1; index < nodeCount; index++) nodes.push(sized(1 + Math.floor(random() * 7), `n${index}`, nodes[Math.floor(random() * index)].id));
    assertMidpointAndNoOverlap(nodes, "down");
  }
});
