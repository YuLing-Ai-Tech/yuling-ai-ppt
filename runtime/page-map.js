// 放映内核 · 页面地图
const mapPanel = document.getElementById("map");
const mapGrid = document.getElementById("map-grid");
const MINI_SCALE_WIDTH = 1920;
let mapBuilt = false;

// 标题优先取大标题，没有再退到金句、小标题
function slideTitle(slide) {
  const heading = ["h1", "h2", ".quote", ".eyebrow"].map(selector => slide.querySelector(selector)).find(Boolean);
  if (!heading) return slide.dataset.section || "";
  // 打字机文字可能写在 .quote 里面的 span 上，还没放映到时 textContent 是空的
  const typed = heading.matches("[data-type]") ? heading : heading.querySelector("[data-type]");
  if (typed) return typed.dataset.type.replace(/\s+/g, " ").trim();
  const copy = heading.cloneNode(true);
  copy.querySelectorAll("br").forEach(lineBreak => lineBreak.replaceWith(" "));
  return copy.textContent.replace(/\s+/g, " ").trim();
}

// 复制一页做缩略图：打字机、数字滚动直接填成最终值
function buildMiniSlide(slide) {
  const copy = slide.cloneNode(true);
  copy.classList.add("active", "settled");
  copy.classList.remove("leaving");
  copy.querySelectorAll("[data-type]").forEach(element => { element.innerHTML = element.dataset.type.replace(/\n/g, "<br>"); });
  copy.querySelectorAll("[data-step]").forEach(element => element.classList.add("step-shown"));
  copy.querySelectorAll("[data-count]").forEach(element => { element.textContent = element.dataset.count + (element.dataset.suffix || ""); });
  const holder = document.createElement("div");
  holder.className = "map-mini";
  holder.appendChild(copy);
  return holder;
}

function buildMap() {
  slides.forEach((slide, index) => {
    const tile = document.createElement("button");
    tile.className = "map-tile" + (slide.classList.contains("chapter") ? " is-chapter" : "");
    tile.style.setProperty("--i", index);
    const screen = document.createElement("div");
    screen.className = "map-screen";
    screen.appendChild(buildMiniSlide(slide));
    const meta = document.createElement("div");
    meta.className = "map-meta";
    meta.innerHTML = `<b>${index + 1}</b><span></span>`;
    meta.querySelector("span").textContent = slideTitle(slide);
    const section = document.createElement("small");
    section.textContent = slide.dataset.section || "";
    tile.append(screen, meta, section);
    tile.addEventListener("click", () => { closeMap(); show(index); });
    mapGrid.appendChild(tile);
  });
  mapBuilt = true;
  fitMiniSlides();
}

function fitMiniSlides() {
  mapGrid.querySelectorAll(".map-screen").forEach(screen => {
    const scale = screen.offsetWidth / MINI_SCALE_WIDTH;
    screen.firstElementChild.style.transform = `scale(${scale})`;
  });
}

function openMap() {
  (window.componentBeforeMapOpen || []).forEach(step => step());  // 组件在缩略图复制前清掉自己的临时状态
  if (!mapBuilt) buildMap();
  document.body.classList.add("map-open");
  const tiles = [...mapGrid.children];
  tiles.forEach((tile, index) => tile.classList.toggle("is-current", index === current));
  requestAnimationFrame(() => {
    fitMiniSlides();
    // 只滚动网格本身；scrollIntoView 会连带把舞台滚上去，标题被切掉
    const currentTile = tiles[current];
    mapGrid.scrollTop = currentTile.offsetTop - (mapGrid.clientHeight - currentTile.offsetHeight) / 2;
    stage.scrollTop = 0;
    currentTile.focus({ preventScroll: true });
  });
}

function closeMap() {
  document.body.classList.remove("map-open");
}

function toggleMap() {
  document.body.classList.contains("map-open") ? closeMap() : openMap();
}

// 地图打开时拦下翻页键，避免在背后翻页
document.addEventListener("keydown", event => {
  const isOpen = document.body.classList.contains("map-open");
  if (event.key.toLowerCase() === "m" && !event.metaKey && !event.ctrlKey && !event.altKey) { toggleMap(); event.stopPropagation(); return; }
  if (!isOpen) return;
  if (event.key === "Escape") closeMap();
  if (event.key !== "Tab" && event.key !== "Enter") event.stopPropagation();
}, true);

document.getElementById("map-toggle").addEventListener("click", toggleMap);
