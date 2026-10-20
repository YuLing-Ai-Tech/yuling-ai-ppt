test("stepStagger：步数少时每步间隔 0.9 秒", () => {
  assertEqual([stepStagger(0), stepStagger(1), stepStagger(2), stepStagger(5)], [0, 0, 0.9, 0.9]);
});

test("stepStagger：步数多时压缩间隔，最后一步在 4.2 秒内开始", () => {
  assertEqual([stepStagger(8) * 7, stepStagger(15) * 14].map(value => Math.round(value * 1000) / 1000), [4.2, 4.2]);
});
