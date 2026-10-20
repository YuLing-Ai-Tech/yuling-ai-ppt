test("整齐刻度：柱图从 0 起，步长取 1/2/5 × 10^k，刻度不超过 6 个", () => {
  assertEqual(niceTicks(0, 91, 6, true), { min: 0, max: 100, step: 20, ticks: [0, 20, 40, 60, 80, 100] });
  assertEqual(niceTicks(-12, 30, 5, true), { min: -20, max: 40, step: 20, ticks: [-20, 0, 20, 40] });
});

test("整齐刻度：折线图不强制含 0；小数步长不带浮点尾巴；一样的值也给出一段", () => {
  assertEqual(niceTicks(72, 95, 6, false).ticks, [70, 75, 80, 85, 90, 95]);
  assertEqual(niceTicks(0.12, 0.47, 5, false).ticks, [0.1, 0.2, 0.3, 0.4, 0.5]);
  assertEqual(niceTicks(5, 5, 5, false), { min: 4, max: 6, step: 2, ticks: [4, 6] });
});

test("线性映射：值越大 y 越小（SVG 的 y 向下）", () => {
  const toY = linearScale([0, 100], [400, 0]);
  assertEqual([toY(0), toY(25), toY(100)], [400, 300, 0]);
});

test("类目分槽：3 个类目分 300 像素，每槽留 40% 空当", () => {
  assertEqual(bandSlots(3, 300, 0.4), [{ center: 50, width: 60 }, { center: 150, width: 60 }, { center: 250, width: 60 }]);
});

test("环饼：按值占比切，从 0 到 1；负数或全 0 不画", () => {
  assertEqual(donutSlices([1, 1, 2]), [{ start: 0, end: 0.25 }, { start: 0.25, end: 0.5 }, { start: 0.5, end: 1 }]);
  assertEqual([donutSlices([3, -1]), donutSlices([0, 0])], [null, null]);
});

test("整齐刻度：刻度数不超过 maxTicks，且覆盖 [min, max]（扫过原来会得到 7 个刻度的区间）", () => {
  assertEqual(niceTicks(-0.5, 0.5, 6, true).ticks.length <= 6, true);
  const tooMany = [];
  for (const includeZero of [true, false]) for (const maxTicks of [3, 4, 5, 6]) {
    for (let low = -30; low <= 30; low += 3) for (let span = 1; span <= 90; span += 4) {
      const [min, max] = [low / 10, low / 10 + span / 10], result = niceTicks(min, max, maxTicks, includeZero);
      const covers = result.min <= min + 1e-9 && result.max >= max - 1e-9 && (!includeZero || (result.min <= 0 && result.max >= 0));
      if (result.ticks.length > maxTicks || !covers) tooMany.push([min, max, maxTicks, includeZero, result.ticks.length]);
    }
  }
  assertEqual(tooMany, []);
});
