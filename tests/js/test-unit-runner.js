test("assertEqual 分得清 undefined 和 null，也分得清 NaN 和 null", () => {
  const rejects = (actual, expected) => {
    try { assertEqual(actual, expected); } catch (error) { return true; }
    return false;
  };
  assertEqual([rejects(undefined, null), rejects([undefined], [null]), rejects({ a: undefined }, {}), rejects(NaN, null)], [true, true, true, true]);
  assertEqual({ a: [1, "x"] }, { a: [1, "x"] });
});

test("异步用例 reject 由 runner 自己记成失败", async () => {
  await Promise.resolve();
  assertEqual(1, 1);
});
