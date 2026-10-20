// 数据图 · 柱、折线、环饼、KPI（设计 §5；Q-017 D7：M4 先做这 4 种）。写法：
//   <figure class="chart" data-chart="bar|line|donut|kpi">，里面放一个 type="application/json" 的 script 元素写数据（JSON）
//   （注意：清单里的 JS 拼进同一个 script 元素，任何 JS 文件里都不能出现结束标签、起始标签或 HTML 注释开头的字面量，见 tests/test_inline_script_safety.py）
//   bar / line：{"labels": ["一班", …], "series": [{"name": "平均分", "values": [86, …]}]}，多组数据就是多根柱、多条线
//   donut：{"labels": ["优", …], "values": [12, …], "center": "45 人"}（center 可省）
//   kpi：{"value": 92.5, "suffix": "%", "label": "及格率", "ratio": 0.925}（ratio 可省，给了就画进度环；数字滚动用内核的 data-count）
// 放映启动时（图元渲染之后）按盒子大小画成 SVG；颜色按组走 --cat-1～8，动效是 CSS 动画（回归能冻结）。
// 数据有错不画，问题进 window.diagramProblems（预览报页码），id 写成"数据图 <类型>"
const CHART_SVG_NS = "http://www.w3.org/2000/svg";
const CHART_MAX_TICKS = 6;
const CHART_PLOT_PADDING = { left: 72, right: 24, top: 40, bottom: 56 };
const CHART_BAR_GAP_RATIO = 0.4;
const CHART_RING_WIDTH_RATIO = 0.16;  // 环宽 = 半径 × 0.16 × 2
const CHART_STAGGER_S = 0.08;
const CHART_MAX_STAGGER_TOTAL_S = 3;  // 错峰总延迟上限：加上柱的 0.9 秒生长和 0.4 秒数值淡入，整页动画在 6 秒内做完
const CHART_LEGEND_HEIGHT = 32;  // 多组数据时，顶部给图例留的高度（柱顶数值标签在柱顶上方 30 像素内）

function chartNode(parent, tag, attributes, text) {
  const node = document.createElementNS(CHART_SVG_NS, tag);
  Object.entries(attributes).forEach(([name, value]) => {
    if (/NaN|Infinity/.test(String(value))) throw new Error(`坐标算出非有限数（${name}=${value}），数值范围太小或数据有误`);
    node.setAttribute(name, value);
  });
  if (text !== undefined) node.textContent = text;
  parent.append(node);
  return node;
}

function chartCanvas(figure) {
  const width = figure.clientWidth, height = figure.clientHeight;
  const svg = chartNode(figure, "svg", { viewBox: `0 0 ${width} ${height}` });
  return { svg, width, height };
}

const seriesTone = index => String(index % 8 + 1);

function checkSeries(data) {
  if (!Array.isArray(data.labels) || !data.labels.length) throw new Error("labels 要写成非空数组");
  if (!Array.isArray(data.series) || !data.series.length) throw new Error("series 要写成非空数组");
  data.series.forEach((series, index) => {
    if (!Array.isArray(series.values) || series.values.length !== data.labels.length || series.values.some(value => !Number.isFinite(value))) {
      throw new Error(`第 ${index + 1} 组 values 要有 ${data.labels.length} 个数`);
    }
  });
}

// 纵轴网格线和刻度、横轴类目名；返回 { toY, slots, plot }
function drawAxes(svg, width, height, data, includeZero) {
  const top = CHART_PLOT_PADDING.top + (data.series.length > 1 ? CHART_LEGEND_HEIGHT : 0);
  const plot = { left: CHART_PLOT_PADDING.left, top, width: width - CHART_PLOT_PADDING.left - CHART_PLOT_PADDING.right,
    height: height - top - CHART_PLOT_PADDING.bottom };
  const values = data.series.flatMap(series => series.values);
  const ticks = niceTicks(Math.min(...values), Math.max(...values), CHART_MAX_TICKS, includeZero);
  const toY = linearScale([ticks.min, ticks.max], [plot.top + plot.height, plot.top]);
  const axes = chartNode(svg, "g", { class: "chart-axes" });
  ticks.ticks.forEach(tick => {
    chartNode(axes, "line", { class: "grid", x1: plot.left, x2: plot.left + plot.width, y1: toY(tick), y2: toY(tick) });
    chartNode(axes, "text", { class: "tick-label", x: plot.left - 14, y: toY(tick), "text-anchor": "end", "dominant-baseline": "middle" }, String(tick));
  });
  const slots = bandSlots(data.labels.length, plot.width, CHART_BAR_GAP_RATIO).map(slot => ({ ...slot, center: plot.left + slot.center }));
  data.labels.forEach((label, index) => chartNode(axes, "text", { class: "cat-label", x: slots[index].center,
    y: plot.top + plot.height + 34, "text-anchor": "middle" }, label));
  return { toY, slots, plot };
}

function drawLegend(svg, width, names) {
  if (names.length < 2) return;
  const legend = chartNode(svg, "g", { class: "chart-legend" });
  names.slice().reverse().forEach((name, reversedIndex) => {
    const index = names.length - 1 - reversedIndex;
    const item = chartNode(legend, "g", { "data-tone": seriesTone(index) });
    const x = width - CHART_PLOT_PADDING.right - (reversedIndex + 1) * 160;
    chartNode(item, "rect", { class: "swatch", x, y: 4, width: 22, height: 12, rx: 3 });
    chartNode(item, "text", { class: "tick-label", x: x + 30, y: 10, "dominant-baseline": "middle" }, name);
  });
}

function drawBarChart(figure, data) {
  checkSeries(data);
  const { svg, width, height } = chartCanvas(figure);
  const { toY, slots } = drawAxes(svg, width, height, data, true);
  const barWidth = slots[0].width / data.series.length;
  const stagger = Math.min(CHART_STAGGER_S, CHART_MAX_STAGGER_TOTAL_S / (slots.length * data.series.length));
  data.series.forEach((series, seriesIndex) => series.values.forEach((value, index) => {
    const x = slots[index].center - slots[index].width / 2 + seriesIndex * barWidth;
    const top = Math.min(toY(value), toY(0)), barHeight = Math.abs(toY(value) - toY(0));
    const toneIndex = data.series.length === 1 ? index : seriesIndex;
    const bar = chartNode(svg, "rect", { class: "bar", "data-tone": seriesTone(toneIndex), x, y: top, width: barWidth, height: barHeight, rx: 8 });
    bar.style.setProperty("--delay", `${(index * data.series.length + seriesIndex) * stagger}s`);
    if (value < 0) bar.classList.add("negative");
    const label = chartNode(svg, "text", { class: "value-label", x: x + barWidth / 2, y: value < 0 ? top + barHeight + 26 : top - 10,
      "text-anchor": "middle" }, String(value));
    label.style.setProperty("--delay", bar.style.getPropertyValue("--delay"));
  }));
  drawLegend(svg, width, data.series.map(series => series.name || ""));
}

function drawLineChart(figure, data) {
  checkSeries(data);
  const { svg, width, height } = chartCanvas(figure);
  const { toY, slots } = drawAxes(svg, width, height, data, false);
  data.series.forEach((series, seriesIndex) => {
    const points = series.values.map((value, index) => ({ x: slots[index].center, y: toY(value) }));
    const line = chartNode(svg, "path", { class: "line", "data-tone": seriesTone(seriesIndex),
      d: points.map((point, index) => `${index ? "L" : "M"} ${point.x} ${point.y}`).join(" ") });
    line.style.setProperty("--len", line.getTotalLength());
    line.style.setProperty("--delay", `${seriesIndex * 0.3}s`);
    points.forEach((point, index) => {
      const dot = chartNode(svg, "circle", { class: "dot", "data-tone": seriesTone(seriesIndex), cx: point.x, cy: point.y, r: 7 });
      dot.style.setProperty("--delay", `${seriesIndex * 0.3 + 1.2 * (index + 1) / points.length}s`);
    });
  });
  drawLegend(svg, width, data.series.map(series => series.name || ""));
}

function drawScatterChart(figure, data) {
  if (!data.xAxis || !data.yAxis || !Array.isArray(data.points) || data.points.length < 3 || data.points.length > 20) throw new Error("散点图需要坐标轴和 3～20 个点");
  const domains = [data.xAxis, data.yAxis];
  if (domains.some(axis => !Number.isFinite(axis.min) || !Number.isFinite(axis.max) || axis.max <= axis.min)) throw new Error("散点图坐标轴范围无效");
  if (data.points.some(point => !point.label || !Number.isFinite(point.x) || !Number.isFinite(point.y) || point.x < data.xAxis.min || point.x > data.xAxis.max || point.y < data.yAxis.min || point.y > data.yAxis.max)) throw new Error("散点必须位于坐标轴范围内");
  const { svg, width, height } = chartCanvas(figure);
  const plot = { left: 86, top: 34, width: width - 126, height: height - 108 };
  const toX = linearScale([data.xAxis.min, data.xAxis.max], [plot.left, plot.left + plot.width]);
  const toY = linearScale([data.yAxis.min, data.yAxis.max], [plot.top + plot.height, plot.top]);
  for (let index = 0; index <= 4; index += 1) {
    const x = plot.left + plot.width * index / 4, y = plot.top + plot.height * index / 4;
    chartNode(svg, "line", { class: "grid", x1: x, x2: x, y1: plot.top, y2: plot.top + plot.height });
    chartNode(svg, "line", { class: "grid", x1: plot.left, x2: plot.left + plot.width, y1: y, y2: y });
  }
  (data.referenceLines || []).forEach(line => {
    if (!line || !["x", "y"].includes(line.axis) || !Number.isFinite(line.value)) throw new Error("散点图基准线无效");
    const vertical = line.axis === "x", position = vertical ? toX(line.value) : toY(line.value);
    chartNode(svg, "line", { class: "scatter-reference", x1: vertical ? position : plot.left, x2: vertical ? position : plot.left + plot.width, y1: vertical ? plot.top : position, y2: vertical ? plot.top + plot.height : position });
    chartNode(svg, "text", { class: "tick-label", x: vertical ? position + 8 : plot.left + 8, y: vertical ? plot.top + 20 : position - 8 }, line.label || "基准");
  });
  const groups = [...new Set(data.points.map(point => point.group || point.label))];
  data.points.forEach((point, index) => {
    const x = toX(point.x), y = toY(point.y), tone = groups.indexOf(point.group || point.label);
    const dot = chartNode(svg, "circle", { class: "scatter-point", "data-tone": seriesTone(tone), cx: x, cy: y, r: 10 });
    dot.style.setProperty("--delay", `${index * 0.07}s`);
    chartNode(svg, "text", { class: "scatter-label", x: x + 14, y: y - 12 }, point.label);
  });
  chartNode(svg, "text", { class: "cat-label", x: plot.left + plot.width / 2, y: height - 15, "text-anchor": "middle" }, data.xAxis.label || "X");
  chartNode(svg, "text", { class: "cat-label", x: 18, y: plot.top + 8 }, data.yAxis.label || "Y");
}

function drawRadarChart(figure, data) {
  if (!Array.isArray(data.axes) || data.axes.length < 4 || data.axes.length > 8 || !Number.isFinite(data.maxValue) || data.maxValue <= 0 || !Array.isArray(data.series) || data.series.length < 1 || data.series.length > 2) throw new Error("雷达图需要 4～8 维、1～2 组数据和有效最大值");
  if (data.series.some(series => !Array.isArray(series.values) || series.values.length !== data.axes.length || series.values.some(value => !Number.isFinite(value) || value < 0 || value > data.maxValue))) throw new Error("雷达图数值必须与维度一致且不超过最大值");
  const { svg, width, height } = chartCanvas(figure);
  const cx = width / 2, cy = height / 2 + 8, radius = Math.min(width, height) * 0.34;
  const pointAt = (axisIndex, ratio) => { const angle = -Math.PI / 2 + axisIndex * Math.PI * 2 / data.axes.length; return { x: cx + Math.cos(angle) * radius * ratio, y: cy + Math.sin(angle) * radius * ratio }; };
  for (let ring = 1; ring <= 4; ring += 1) chartNode(svg, "polygon", { class: "radar-grid", points: data.axes.map((_, index) => { const point = pointAt(index, ring / 4); return `${point.x},${point.y}`; }).join(" ") });
  data.axes.forEach((label, index) => { const edge = pointAt(index, 1); const text = pointAt(index, 1.13); chartNode(svg, "line", { class: "radar-grid", x1: cx, y1: cy, x2: edge.x, y2: edge.y }); chartNode(svg, "text", { class: "radar-label", x: text.x, y: text.y, "text-anchor": text.x < cx - 4 ? "end" : text.x > cx + 4 ? "start" : "middle", "dominant-baseline": "middle" }, label); });
  data.series.forEach((series, seriesIndex) => {
    const polygon = chartNode(svg, "polygon", { class: "radar-series", "data-tone": seriesTone(seriesIndex), points: series.values.map((value, index) => { const point = pointAt(index, value / data.maxValue); return `${point.x},${point.y}`; }).join(" ") });
    polygon.style.setProperty("--delay", `${seriesIndex * 0.25}s`);
  });
  drawLegend(svg, width, data.series.map(series => series.name || ""));
}

function drawStackedBarChart(figure, data) {
  checkSeries(data);
  if (data.series.length < 2 || data.series.length > 5 || data.series.some(series => series.values.some(value => value < 0))) throw new Error("堆叠图需要 2～5 组非负数据");
  const totals = data.labels.map((_, labelIndex) => data.series.reduce((sum, series) => sum + series.values[labelIndex], 0));
  if (data.mode === "percent" && totals.some(total => Math.abs(total - 100) > 0.1)) throw new Error("100% 堆叠图每个类目必须合计 100");
  const normalized = { labels: data.labels, series: [{ name: "total", values: totals }] };
  const { svg, width, height } = chartCanvas(figure);
  const { toY, slots, plot } = drawAxes(svg, width, height, normalized, true);
  const barWidth = Math.min(slots[0].width * 0.72, 90);
  data.labels.forEach((_, labelIndex) => {
    let cumulative = 0;
    data.series.forEach((series, seriesIndex) => {
      const value = series.values[labelIndex], top = toY(cumulative + value), bottom = toY(cumulative);
      const segment = chartNode(svg, "rect", { class: "stack-segment", "data-tone": seriesTone(seriesIndex), x: slots[labelIndex].center - barWidth / 2, y: top, width: barWidth, height: Math.max(0, bottom - top), rx: seriesIndex === data.series.length - 1 ? 7 : 0 });
      segment.style.setProperty("--delay", `${(labelIndex * data.series.length + seriesIndex) * 0.06}s`);
      cumulative += value;
    });
    chartNode(svg, "text", { class: "value-label", x: slots[labelIndex].center, y: Math.max(plot.top + 18, toY(cumulative) - 10), "text-anchor": "middle" }, String(chartRound(cumulative)));
  });
  drawLegend(svg, width, data.series.map(series => series.name || ""));
}

function drawHeatmapChart(figure, data) {
  if (!Array.isArray(data.columns) || data.columns.length < 3 || data.columns.length > 8 || !Array.isArray(data.rows) || data.rows.length < 3 || data.rows.length > 10) throw new Error("热力矩阵需要 3～8 列和 3～10 行");
  if (data.rows.some(row => !row.label || !Array.isArray(row.values) || row.values.length !== data.columns.length || row.values.some(value => !Number.isFinite(value)))) throw new Error("热力矩阵每行数值必须与列数一致");
  if (data.colorScale === "diverging" && !Number.isFinite(data.midpoint)) throw new Error("发散色阶需要 midpoint");
  const { svg, width, height } = chartCanvas(figure);
  const left = 150, top = 52, right = 24, bottom = 20, cellWidth = (width - left - right) / data.columns.length, cellHeight = (height - top - bottom) / data.rows.length;
  const values = data.rows.flatMap(row => row.values), min = Math.min(...values), max = Math.max(...values), midpoint = data.colorScale === "diverging" ? data.midpoint : min;
  data.columns.forEach((label, index) => chartNode(svg, "text", { class: "heatmap-label", x: left + (index + 0.5) * cellWidth, y: 28, "text-anchor": "middle" }, label));
  data.rows.forEach((row, rowIndex) => {
    chartNode(svg, "text", { class: "heatmap-label", x: left - 14, y: top + (rowIndex + 0.5) * cellHeight, "text-anchor": "end", "dominant-baseline": "middle" }, row.label);
    row.values.forEach((value, columnIndex) => {
      const denominator = value >= midpoint ? Math.max(max - midpoint, 1e-9) : Math.max(midpoint - min, 1e-9);
      const intensity = Math.min(1, Math.abs(value - midpoint) / denominator);
      const tone = data.colorScale === "diverging" && value < midpoint ? 8 : 1;
      const cell = chartNode(svg, "rect", { class: "heatmap-cell", "data-tone": seriesTone(tone - 1), "fill-opacity": chartRound(0.14 + intensity * 0.78), x: left + columnIndex * cellWidth + 3, y: top + rowIndex * cellHeight + 3, width: Math.max(1, cellWidth - 6), height: Math.max(1, cellHeight - 6), rx: 8 });
      cell.style.setProperty("--delay", `${rowIndex * 0.07 + columnIndex * 0.02}s`);
      chartNode(svg, "text", { class: "heatmap-value", x: left + (columnIndex + 0.5) * cellWidth, y: top + (rowIndex + 0.5) * cellHeight, "text-anchor": "middle", "dominant-baseline": "middle" }, String(value));
    });
  });
}

// 环：每段是一个 pathLength=100 的圆，dasharray 取它占的长度，dashoffset 把它转到起点（CSS 把圆转 -90° 从 12 点钟开始）
function drawDonutChart(figure, data) {
  const slices = Array.isArray(data.values) && data.values.every(Number.isFinite) ? donutSlices(data.values) : null;
  if (!slices || !Array.isArray(data.labels) || data.labels.length !== data.values.length) {
    throw new Error("values 要是和 labels 一样多的非负数，且不全为 0");
  }
  const { svg, width, height } = chartCanvas(figure);
  const radius = Math.min(width * 0.5, height) * 0.4, centerX = width * 0.32, centerY = height / 2;
  slices.forEach((slice, index) => {
    const arc = chartNode(svg, "circle", { class: "slice", "data-tone": seriesTone(index), cx: centerX, cy: centerY, r: radius, pathLength: 100,
      "stroke-width": radius * CHART_RING_WIDTH_RATIO * 2, "stroke-dasharray": `${chartRound((slice.end - slice.start) * 100)} 100`,
      "stroke-dashoffset": chartRound(-slice.start * 100) });
    arc.style.setProperty("--delay", `${index * 0.25}s`);
    const legendY = centerY - (slices.length - 1) * 28 + index * 56;
    chartNode(svg, "rect", { class: "swatch", "data-tone": seriesTone(index), x: width * 0.62, y: legendY - 8, width: 22, height: 16, rx: 4 });
    chartNode(svg, "text", { class: "cat-label", x: width * 0.62 + 36, y: legendY, "dominant-baseline": "middle" },
      `${data.labels[index]}  ${Math.round((slice.end - slice.start) * 100)}%`);
  });
  if (data.center) chartNode(svg, "text", { class: "center-label", x: centerX, y: centerY, "text-anchor": "middle", "dominant-baseline": "middle" }, data.center);
}

// KPI：大数字（data-count 交给内核滚动）+ 名称；给了 ratio 就在数字外画一圈进度
function drawKpi(figure, data) {
  if (!Number.isFinite(data.value)) throw new Error("value 要写数字");
  if (data.ratio !== undefined && !(data.ratio >= 0 && data.ratio <= 1)) throw new Error("ratio 要在 0～1 之间");
  if (data.ratio !== undefined) {
    const { svg, width, height } = chartCanvas(figure);
    const radius = Math.min(width, height) * 0.42;
    chartNode(svg, "circle", { class: "ring-track", cx: width / 2, cy: height / 2, r: radius, "stroke-width": radius * 0.12 });
    chartNode(svg, "circle", { class: "slice", "data-tone": "1", cx: width / 2, cy: height / 2, r: radius, pathLength: 100,
      "stroke-width": radius * 0.12, "stroke-dasharray": `${chartRound(data.ratio * 100)} 100`, "stroke-dashoffset": 0 });
  }
  const value = document.createElement("div");
  value.className = "kpi-value";
  value.dataset.count = String(data.value);
  if (data.suffix) value.dataset.suffix = data.suffix;
  value.textContent = `${data.value}${data.suffix || ""}`;
  const label = document.createElement("div");
  label.className = "kpi-label";
  label.textContent = data.label || "";
  figure.append(value, label);
}

function drawFunnelChart(figure, data) {
  if (!Array.isArray(data.stages) || data.stages.length < 3 || data.stages.length > 6) throw new Error("stages 要有 3～6 项");
  if (data.stages.some((stage, index) => !stage || !stage.label || !Number.isFinite(stage.value) || stage.value < 0 || (index && stage.value > data.stages[index - 1].value))) {
    throw new Error("漏斗数值必须为非负数并按阶段递减");
  }
  const { svg, width, height } = chartCanvas(figure);
  const max = data.stages[0].value || 1, center = width / 2, gap = 10;
  const rowHeight = (height - 42 - gap * (data.stages.length - 1)) / data.stages.length;
  data.stages.forEach((stage, index) => {
    const next = data.stages[index + 1]?.value ?? stage.value * 0.72;
    const topWidth = Math.max(width * 0.28, width * 0.82 * stage.value / max);
    const bottomWidth = Math.max(width * 0.24, width * 0.82 * next / max);
    const y = index * (rowHeight + gap);
    const polygon = chartNode(svg, "polygon", { class: "funnel-stage", "data-tone": seriesTone(index), points: `${center - topWidth / 2},${y} ${center + topWidth / 2},${y} ${center + bottomWidth / 2},${y + rowHeight} ${center - bottomWidth / 2},${y + rowHeight}` });
    polygon.style.setProperty("--delay", `${index * 0.12}s`);
    chartNode(svg, "text", { class: "funnel-label", x: center, y: y + rowHeight / 2 - 4, "text-anchor": "middle" }, stage.label);
    const ratio = index ? Math.round(stage.value / max * 100) + "%" : "100%";
    chartNode(svg, "text", { class: "funnel-value", x: center, y: y + rowHeight / 2 + 24, "text-anchor": "middle" }, `${stage.value}${data.unit || ""} · ${ratio}`);
  });
}

function drawMatrixChart(figure, data) {
  if (!data.axes || !Array.isArray(data.quadrants) || data.quadrants.length !== 4 || !Array.isArray(data.points) || data.points.length < 2) throw new Error("矩阵需要四象限、坐标轴和至少两个点");
  if (data.points.some(point => !point.label || !Number.isFinite(point.x) || !Number.isFinite(point.y) || point.x < 0 || point.x > 100 || point.y < 0 || point.y > 100)) throw new Error("矩阵坐标必须在 0～100");
  const { svg, width, height } = chartCanvas(figure);
  const plot = { left: 100, top: 42, width: width - 170, height: height - 110 };
  const quadrantPositions = [[0, 0], [1, 0], [0, 1], [1, 1]];
  quadrantPositions.forEach(([column, row], index) => {
    chartNode(svg, "rect", { class: "matrix-quadrant", "data-tone": seriesTone(index + 1), x: plot.left + column * plot.width / 2, y: plot.top + row * plot.height / 2, width: plot.width / 2, height: plot.height / 2 });
    chartNode(svg, "text", { class: "matrix-quadrant-label", x: plot.left + (column + 0.5) * plot.width / 2, y: plot.top + row * plot.height / 2 + 30, "text-anchor": "middle" }, data.quadrants[index]);
  });
  chartNode(svg, "line", { class: "matrix-axis", x1: plot.left, x2: plot.left + plot.width, y1: plot.top + plot.height / 2, y2: plot.top + plot.height / 2 });
  chartNode(svg, "line", { class: "matrix-axis", x1: plot.left + plot.width / 2, x2: plot.left + plot.width / 2, y1: plot.top, y2: plot.top + plot.height });
  chartNode(svg, "text", { class: "cat-label", x: plot.left, y: plot.top + plot.height + 38, "text-anchor": "start" }, data.axes.xLow);
  chartNode(svg, "text", { class: "cat-label", x: plot.left + plot.width, y: plot.top + plot.height + 38, "text-anchor": "end" }, data.axes.xHigh);
  chartNode(svg, "text", { class: "cat-label", x: 22, y: plot.top + plot.height, "text-anchor": "start" }, data.axes.yLow);
  chartNode(svg, "text", { class: "cat-label", x: 22, y: plot.top + 12, "text-anchor": "start" }, data.axes.yHigh);
  data.points.forEach((point, index) => {
    const x = plot.left + point.x / 100 * plot.width, y = plot.top + (100 - point.y) / 100 * plot.height;
    chartNode(svg, "circle", { class: "matrix-point", "data-tone": seriesTone(index), cx: x, cy: y, r: 10 });
    chartNode(svg, "text", { class: "matrix-point-label", x: x + 15, y: y - 12 }, point.label);
  });
}

function drawRankingChart(figure, data) {
  if (!Array.isArray(data.entries) || data.entries.length < 3 || data.entries.length > 8 || data.entries.some(entry => !entry.label || !Number.isFinite(entry.value))) throw new Error("排名需要 3～8 个有效条目");
  const entries = data.entries.slice().sort((a, b) => b.value - a.value);
  const { svg, width, height } = chartCanvas(figure);
  const labelWidth = Math.min(240, width * 0.22), valueWidth = 150, top = 18, gap = 10;
  const rowHeight = (height - top * 2 - gap * (entries.length - 1)) / entries.length;
  const max = Math.max(...entries.map(entry => Math.abs(entry.value)), 1);
  entries.forEach((entry, index) => {
    const y = top + index * (rowHeight + gap);
    chartNode(svg, "text", { class: "ranking-label", x: labelWidth - 16, y: y + rowHeight / 2, "text-anchor": "end", "dominant-baseline": "middle" }, `${index + 1}. ${entry.label}`);
    const barWidth = (width - labelWidth - valueWidth) * Math.max(0, entry.value) / max;
    const bar = chartNode(svg, "rect", { class: "ranking-bar", "data-tone": seriesTone(index), x: labelWidth, y: y + 5, width: barWidth, height: rowHeight - 10, rx: Math.min(12, rowHeight / 2) });
    bar.style.setProperty("--delay", `${index * 0.08}s`);
    const change = Number.isFinite(entry.change) ? `  ${entry.change >= 0 ? "↑" : "↓"}${Math.abs(entry.change)}` : "";
    chartNode(svg, "text", { class: "ranking-value", x: labelWidth + barWidth + 14, y: y + rowHeight / 2, "dominant-baseline": "middle" }, `${entry.value}${data.unit || ""}${change}`);
  });
}

const CHART_DRAWERS = { bar: drawBarChart, line: drawLineChart, donut: drawDonutChart, kpi: drawKpi, funnel: drawFunnelChart, matrix: drawMatrixChart, ranking: drawRankingChart, scatter: drawScatterChart, radar: drawRadarChart, "stacked-bar": drawStackedBarChart, heatmap: drawHeatmapChart };

function renderSlideCharts(slide, index) {
  slide.querySelectorAll("figure.chart").forEach(figure => {
    // 非当前页在放映内核中不可见，启动阶段宽高为 0。延迟到页面真正激活后再画，
    // 否则 SVG 虽然存在，柱、轴和标签却都会被算成 0 宽，形成“有 DOM 的空白图”。
    if (figure.clientWidth < 1 || figure.clientHeight < 1) {
      figure.dataset.chartPending = "true";
      return;
    }
    const type = figure.dataset.chart;
    const problemId = `数据图 ${type || "（没写类型）"}`;
    window.diagramProblems = window.diagramProblems.filter(problem => !(problem.page === index + 1 && problem.id === problemId));
    figure.querySelectorAll(":scope > svg, :scope > .kpi-value, :scope > .kpi-label").forEach(drawn => drawn.remove());
    try {
      if (!CHART_DRAWERS[type]) throw new Error(`data-chart 只能是 ${Object.keys(CHART_DRAWERS).join("、")}`);
      const source = figure.querySelector('script[type="application/json"]');
      if (!source) throw new Error('缺少 type="application/json" 的数据块');
      CHART_DRAWERS[type](figure, JSON.parse(source.textContent));
      delete figure.dataset.chartPending;
      figure.dataset.chartRendered = "true";
    } catch (error) {
      figure.querySelectorAll(":scope > svg, :scope > .kpi-value, :scope > .kpi-label").forEach(drawn => drawn.remove());  // 画到一半出错：不留半张图
      delete figure.dataset.chartRendered;
      window.diagramProblems.push({ page: index + 1, id: problemId, problem: error.message });
      console.error(`数据图：第 ${index + 1} 页 ${type}：${error.message}`);
    }
  });
}

function renderAllCharts() {
  slides.forEach((slide, index) => renderSlideCharts(slide, index));
}

(window.componentBootSteps = window.componentBootSteps || []).push(renderAllCharts);
(window.componentEnterSteps = window.componentEnterSteps || []).push(slide => renderSlideCharts(slide, slides.indexOf(slide)));
