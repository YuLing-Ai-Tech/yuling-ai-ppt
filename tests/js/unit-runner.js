// 前端单元测试小框架：在 playwright 打开的空白页里跑，不引入 npm 依赖（设计 §6 第 2 项）
const unitTests = [];

function test(name, body) {
  unitTests.push({ name, body });
}

// JSON.stringify 会把 undefined 当成缺失/null、把 NaN 和 Infinity 当成 null，这里先换成带标记的字符串再比
function stringifyStrict(value) {
  return JSON.stringify(value, (key, item) => {
    if (item === undefined) return "<undefined>";
    if (typeof item === "number" && !Number.isFinite(item)) return `<${item}>`;
    return item;
  });
}

function assertEqual(actual, expected, note = "") {
  const actualText = stringifyStrict(actual), expectedText = stringifyStrict(expected);
  if (actualText !== expectedText) throw new Error(`${note}期望 ${expectedText}，实际 ${actualText}`);
}

async function runUnitTests() {
  const results = [];
  for (const { name, body } of unitTests) {
    try {
      await body();
      results.push({ name, ok: true });
    } catch (error) {
      results.push({ name, ok: false, message: String(error && error.message || error) });
    }
  }
  return results;
}
