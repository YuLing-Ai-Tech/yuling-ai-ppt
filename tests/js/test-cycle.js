// 循环图纯函数：24×12 图区、节点 4×1.6；环的横半径 12 - 2 - 0.3 = 9.7，纵半径 6 - 0.8 - 0.3 = 4.9
test("4 个节点：正上、正右、正下、正左，顺时针", () => {
  const places = layoutCycle(4, { columns: 24, rows: 12 }, { w: 4, h: 1.6 });
  assertEqual(places.map(({ column, row }) => [column, row]), [[10, 0.3], [19.7, 5.2], [10, 10.1], [0.3, 5.2]]);
});

test("连线顺着环走：上→右 出右边进上边，右→下 出下边进右边，下→左，左→上", () => {
  const angles = layoutCycle(4, { columns: 24, rows: 12 }, { w: 4, h: 1.6 }).map(place => place.angle);
  assertEqual([0, 1, 2, 3].map(index => cycleEdgeSides(angles[index], angles[(index + 1) % 4]).join("")), ["rt", "br", "lb", "tl"]);
});

test("3 个节点：第 1 个在正上，另两个在下半圈左右对称", () => {
  const [top, right, left] = layoutCycle(3, { columns: 24, rows: 12 }, { w: 4, h: 1.6 });
  assertEqual([top.column, right.row === left.row, cycleRound(right.column + left.column)], [10, true, 20]);
});
