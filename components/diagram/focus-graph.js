// 图元 · 聚焦要留下哪些（设计 §4.3）。纯函数，不碰 DOM
// graph：{ parents: { id: 父容器 id 或 null }, edges: [{ id, from, to }] }

function descendantsOf(parents, id) {
  const children = Object.keys(parents).filter(childId => parents[childId] === id);
  return children.flatMap(childId => [childId, ...descendantsOf(parents, childId)]);
}

function ancestorsOf(parents, id) {
  const chain = [];
  for (let parent = parents[id]; parent && !chain.includes(parent); parent = parents[parent]) chain.push(parent);
  return chain;
}

function withAncestors(parents, ids) {
  const kept = new Set(ids);
  ids.forEach(id => ancestorsOf(parents, id).forEach(parent => kept.add(parent)));
  return kept;
}

// 点中的节点或容器（容器连同全部子孙）算"它本身"，再沿连线向外 depth 层；留下的节点的祖先容器也留下，免得节点悬空
// 返回 { boxes: [id…], edges: [id…] }，各自排好序
function focusKeepSet(graph, startIds, depth) {
  const reached = new Set(startIds.flatMap(id => [id, ...descendantsOf(graph.parents, id)]));
  const keptEdges = new Set();
  let frontier = new Set(reached);
  for (let level = 0; level < depth; level++) {
    const next = new Set();
    graph.edges.forEach(edge => {
      if (!frontier.has(edge.from) && !frontier.has(edge.to)) return;
      keptEdges.add(edge.id);
      [edge.from, edge.to].filter(end => !reached.has(end)).forEach(end => { reached.add(end); next.add(end); });
    });
    frontier = next;
  }
  return { boxes: [...withAncestors(graph.parents, [...reached])].sort(), edges: [...keptEdges].sort() };
}

// 高亮路径：只留这串节点和相邻两个之间的连线（哪个方向都算）
function routeKeepSet(graph, nodeIds) {
  const pairs = new Set(nodeIds.slice(1).flatMap((id, index) => [`${nodeIds[index]}→${id}`, `${id}→${nodeIds[index]}`]));
  const edges = graph.edges.filter(edge => pairs.has(`${edge.from}→${edge.to}`)).map(edge => edge.id);
  return { boxes: [...withAncestors(graph.parents, nodeIds)].sort(), edges: [...new Set(edges)].sort() };
}
