// 图元 · 聚焦（设计 §4.3）：点节点或容器，只留它和直接关联的部分，其余压暗（或隐藏）。默认关闭，回归截图不受影响
// 再点一次、点空白处、按 Esc 或换页恢复；数字键 1 / 2 切换关联层数；D 切换压暗 / 隐藏；R 依次高亮本页 .route 写的路径
const FOCUS_HIDE_BY_DEFAULT = false;  // false = 默认压暗（Q-011 已定）；改 true 则默认隐藏
let focusDepth = 1;
let focusTarget = null;  // { dg, ids: [id…], routeIndex }；routeIndex 为 -1 表示点选，不是路径

function focusGraph(dg) {
  const parents = {};
  dg.querySelectorAll(".dg-part[data-id]").forEach(element => { parents[element.dataset.id] = element.dataset.in || null; });
  const edges = [...dg.querySelectorAll(".edge")].map(element => ({
    id: edgeIdOf(element), from: parseEndpoint(element.dataset.from).id, to: parseEndpoint(element.dataset.to).id }));
  return { parents, edges };
}

function clearFocusMarks() {
  document.querySelectorAll(".dg.is-focusing").forEach(dg => {
    dg.classList.remove("is-focusing");
    dg.querySelectorAll(".is-kept").forEach(part => part.classList.remove("is-kept"));
  });
}

function clearFocus() {
  clearFocusMarks();
  focusTarget = null;
}

function applyFocus() {
  const { dg, ids, routeIndex } = focusTarget;
  const graph = focusGraph(dg);
  const keep = routeIndex >= 0 ? routeKeepSet(graph, ids) : focusKeepSet(graph, ids, focusDepth);
  const boxes = new Set(keep.boxes), edges = new Set(keep.edges);
  clearFocusMarks();
  dg.querySelectorAll(".dg-part").forEach(part => part.classList.toggle("is-kept", boxes.has(part.dataset.id) || edges.has(part.dataset.edge)));
  dg.classList.add("is-focusing");
}

function focusOnClick(event) {
  const dg = event.target.closest(".dg");
  const part = event.target.closest(".dg-part[data-id]");
  if (!dg || dg.closest(".slide") !== slides[current] || !part) {  // 页面地图缩略图里的克隆页也落在这里：不算聚焦
    clearFocus();
    return;
  }
  const clickedAgain = focusTarget && focusTarget.routeIndex < 0 && focusTarget.dg === dg && focusTarget.ids[0] === part.dataset.id;
  if (clickedAgain) {
    clearFocus();
    return;
  }
  focusTarget = { dg, ids: [part.dataset.id], routeIndex: -1 };
  applyFocus();
}

function cycleRoute() {
  const routes = [...slides[current].querySelectorAll(".dg .route[data-nodes]")];
  if (!routes.length) return;  // 本页没写路径（或路径都缺 data-nodes，预览会报）：不动已有的点选聚焦
  const nextIndex = focusTarget && focusTarget.routeIndex >= 0 ? focusTarget.routeIndex + 1 : 0;
  if (nextIndex >= routes.length) {
    clearFocus();
    return;
  }
  focusTarget = { dg: routes[nextIndex].closest(".dg"), ids: routes[nextIndex].dataset.nodes.trim().split(/\s+/), routeIndex: nextIndex };
  applyFocus();
}

document.addEventListener("click", focusOnClick);
document.addEventListener("keydown", event => {
  if (event.metaKey || event.ctrlKey || event.altKey) return;  // Ctrl/Cmd+R 刷新、Cmd+D 加书签等是浏览器的
  const key = event.key.toLowerCase();
  if (key === "escape") clearFocus();
  else if (key === "1" || key === "2") {
    focusDepth = Number(key);
    if (focusTarget && focusTarget.routeIndex < 0) applyFocus();
  } else if (key === "d") document.body.classList.toggle("focus-hide");
  else if (key === "r") cycleRoute();
});
if (FOCUS_HIDE_BY_DEFAULT) document.body.classList.add("focus-hide");
(window.componentEnterSteps = window.componentEnterSteps || []).push(clearFocus);
(window.componentBeforeMapOpen = window.componentBeforeMapOpen || []).push(clearFocus);
