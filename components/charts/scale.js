// 数据图 · 比例尺（设计 §5）：整齐刻度、线性映射、类目分槽、环形扇区。纯函数，不碰 DOM
const CHART_NICE_MULTIPLES = [1, 2, 5, 10];
const CHART_PRECISION = 1e6;

const chartRound = value => Math.round(value * CHART_PRECISION) / CHART_PRECISION;

// 1 → 2 → 5 → 10 → 20 …：比 step 大的下一档整齐步长
function nextNiceStep(step) {
  const decade = Math.pow(10, Math.floor(Math.log10(step) + 1e-9));
  const mantissa = step / decade;
  return (mantissa < 2 - 1e-9 ? 2 : mantissa < 5 - 1e-9 ? 5 : 10) * decade;
}

// 把 [min, max] 扩成整齐的刻度：步长取 1、2、5 × 10 的整数次方，刻度最多 maxTicks 个；includeZero 时 0 一定在轴上（柱子从 0 长出）
// 返回 { min, max, step, ticks }
function niceTicks(min, max, maxTicks, includeZero) {
  const low = includeZero ? Math.min(0, min) : min, high = includeZero ? Math.max(0, max) : max;
  const rough = (high - low || Math.abs(high) || 1) / Math.max(1, maxTicks - 1);
  const power = Math.pow(10, Math.floor(Math.log10(rough)));
  let step = CHART_NICE_MULTIPLES.map(multiple => multiple * power).find(candidate => candidate >= rough * (1 - 1e-9));
  let start, end, count;
  for (;;) {  // 扩到整齐刻度后刻度数可能超过 maxTicks：步长升一档再试
    start = Math.floor(chartRound(low / step)) * step;
    end = Math.ceil(chartRound(high / step)) * step;
    if (end <= start) end = start + step;
    count = Math.round((end - start) / step);
    if (!(count + 1 > Math.max(2, maxTicks))) break;
    step = nextNiceStep(step);
  }
  return { min: chartRound(start), max: chartRound(end), step: chartRound(step),
    ticks: Array.from({ length: count + 1 }, (_, index) => chartRound(start + index * step)) };
}

// 线性映射：domain [d0, d1] → range [r0, r1]
function linearScale([d0, d1], [r0, r1]) {
  return value => r0 + (value - d0) / (d1 - d0) * (r1 - r0);
}

// count 个类目平分 length，每槽留 gapRatio 的空当；返回 [{ center, width }]（width 是柱组的宽度）
function bandSlots(count, length, gapRatio) {
  const slot = length / count;
  return Array.from({ length: count }, (_, index) => ({ center: chartRound(slot * (index + 0.5)), width: chartRound(slot * (1 - gapRatio)) }));
}

// 环饼：每个值占的起止比例（0～1，从 12 点钟方向顺时针）；有负数或全为 0 时返回 null
function donutSlices(values) {
  const total = values.reduce((sum, value) => sum + value, 0);
  if (values.some(value => value < 0) || total <= 0) return null;
  let start = 0;
  return values.map(value => {
    const slice = { start: chartRound(start / total), end: chartRound((start + value) / total) };
    start += value;
    return slice;
  });
}
