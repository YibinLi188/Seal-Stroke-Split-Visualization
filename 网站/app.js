const state = {
  examples: [],
  record: null,
  mode: "animate",
  step: 0,
  playing: false,
  timer: null,
  speed: 850,
};

const exampleList = document.querySelector("#example-list");
const exampleCount = document.querySelector("#example-count");
const exampleTotal = document.querySelector("#example-total");
const viewerTitle = document.querySelector("#viewer-title");
const viewerSubtitle = document.querySelector("#viewer-subtitle");
const viewerStage = document.querySelector("#viewer-stage");
const strokeLegend = document.querySelector("#stroke-legend");
const progressLabel = document.querySelector("#progress-label");
const resultNote = document.querySelector("#result-note");
const playButton = document.querySelector("#play-button");
const resetButton = document.querySelector("#reset-button");
const prevButton = document.querySelector("#prev-button");
const nextButton = document.querySelector("#next-button");
const speedInput = document.querySelector("#speed-input");
const speedValue = document.querySelector("#speed-value");
const imageInput = document.querySelector("#image-input");
const uploadZone = document.querySelector("#upload-zone");

async function getJson(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "请求失败");
  return payload;
}

function setResultNote(text, isError = false) {
  resultNote.textContent = text;
  resultNote.classList.toggle("is-error", isError);
}

function stopPlayback() {
  state.playing = false;
  if (state.timer) window.clearInterval(state.timer);
  state.timer = null;
  playButton.textContent = "开始播放";
}

function renderExampleList() {
  exampleList.innerHTML = "";
  if (!state.examples.length) {
    exampleList.innerHTML = '<p class="loading-line">暂时没有可用样例</p>';
    return;
  }
  state.examples.forEach((example) => {
    const button = document.createElement("button");
    button.className = "example-button";
    button.type = "button";
    button.dataset.id = example.id;
    button.innerHTML = `<span class="example-character">${example.character}</span><span class="example-info"><strong>${example.source_name}</strong><small>${example.overlap_pixel_count ? `重叠 ${example.overlap_pixel_count} 像素` : "无重叠"}</small></span><span class="example-strokes">${example.segment_count} 笔</span>`;
    button.addEventListener("click", () => loadExample(example.id, button));
    exampleList.appendChild(button);
  });
}

function markActiveExample(button) {
  document.querySelectorAll(".example-button").forEach((item) => item.classList.toggle("is-active", item === button));
}

function renderLegend() {
  strokeLegend.innerHTML = "";
  if (!state.record) return;
  state.record.strokes.forEach((stroke) => {
    const chip = document.createElement("span");
    chip.className = `stroke-chip${stroke.id <= state.step ? " is-current" : ""}`;
    chip.style.setProperty("--chip-color", stroke.color);
    chip.innerHTML = `<button type="button" data-step="${stroke.id}"><i class="stroke-swatch"></i>第 ${stroke.id} 笔</button>`;
    chip.querySelector("button").addEventListener("click", () => setStep(stroke.id));
    strokeLegend.appendChild(chip);
  });
}

const SVG_NS = "http://www.w3.org/2000/svg";

function svgElement(tag, attributes = {}) {
  const element = document.createElementNS(SVG_NS, tag);
  Object.entries(attributes).forEach(([name, value]) => element.setAttribute(name, value));
  return element;
}

function makeStrokePath(points) {
  if (!Array.isArray(points) || !points.length) return "";
  return points
    .filter((point) => Array.isArray(point) && point.length >= 2)
    .map(([y, x], index) => `${index ? "L" : "M"} ${Number(x)} ${Number(y)}`)
    .join(" ");
}

function estimateRevealWidth(stroke) {
  const pointCount = Math.max(1, Number(stroke.point_count) || (stroke.points || []).length);
  const pixelCount = Math.max(1, Number(stroke.pixel_count) || pointCount);
  return Math.max(1.4, Math.min(5, (pixelCount / pointCount) * 1.05));
}

function appendStroke(svg, stroke, animate) {
  const pathData = makeStrokePath(stroke.points);
  if (!animate || !pathData) {
    const image = svgElement("image", {
      class: "stroke-image",
      href: stroke.url,
      x: 0,
      y: 0,
      width: state.record.width,
      height: state.record.height,
      preserveAspectRatio: "none",
      "aria-label": `第 ${stroke.id} 笔`,
    });
    svg.appendChild(image);
    return;
  }

  const revealPath = svgElement("path", {
    class: "draw-path",
    d: pathData,
    fill: "none",
    stroke: stroke.color,
    "stroke-linecap": "round",
    "stroke-linejoin": "round",
  });
  revealPath.style.strokeWidth = `${estimateRevealWidth(stroke)}px`;
  svg.appendChild(revealPath);

  requestAnimationFrame(() => {
    const length = revealPath.getTotalLength();
    if (!Number.isFinite(length) || length <= 0) {
      return;
    }
    revealPath.style.strokeDasharray = `${length} ${length}`;
    revealPath.style.strokeDashoffset = `${length}`;
    revealPath.style.transition = `stroke-dashoffset ${Math.max(180, state.speed - 120)}ms linear`;
    requestAnimationFrame(() => { revealPath.style.strokeDashoffset = "0"; });
  });
}

function renderStage() {
  if (!state.record) return;
  viewerStage.innerHTML = "";
  if (state.mode === "overview") {
    viewerStage.className = "viewer-stage overview-stage";
    viewerStage.innerHTML = `<div class="overview-grid"><figure><figcaption>输入金文</figcaption><img src="${state.record.input_url}" alt="${state.record.character} 原始金文图像" /></figure><figure><figcaption>笔画叠加结果</figcaption><img src="${state.record.overlay_url}" alt="${state.record.character} 笔画叠加结果" /></figure></div>`;
    return;
  }
  viewerStage.className = "viewer-stage stroke-mode";
  const canvas = document.createElement("div");
  canvas.className = "stroke-canvas";
  canvas.style.setProperty("--canvas-ratio", `${state.record.width} / ${state.record.height}`);
  const svg = svgElement("svg", {
    class: "stroke-drawing",
    viewBox: `0 0 ${state.record.width} ${state.record.height}`,
    preserveAspectRatio: "none",
    role: "img",
    "aria-label": `${state.record.character} 笔画书写过程`,
  });
  state.record.strokes.forEach((stroke) => {
    if (stroke.id <= state.step) appendStroke(svg, stroke, stroke.id === state.step);
  });
  canvas.appendChild(svg);
  viewerStage.appendChild(canvas);
}

function setStep(step) {
  if (!state.record) return;
  state.step = Math.max(0, Math.min(step, state.record.strokes.length));
  renderStage();
  renderLegend();
  progressLabel.textContent = `${state.step} / ${state.record.strokes.length} 笔`;
  resetButton.disabled = false;
  prevButton.disabled = state.step === 0;
  nextButton.disabled = state.step >= state.record.strokes.length;
}

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll(".mode-button").forEach((button) => button.classList.toggle("is-active", button.dataset.mode === mode));
  renderStage();
}

function startPlayback() {
  if (!state.record) return;
  if (state.step >= state.record.strokes.length) setStep(0);
  stopPlayback();
  state.playing = true;
  playButton.textContent = "暂停播放";
  state.timer = window.setInterval(() => {
    if (state.step >= state.record.strokes.length) {
      stopPlayback();
      return;
    }
    setStep(state.step + 1);
  }, state.speed);
}

function loadRecord(record, sourceLabel) {
  stopPlayback();
  state.record = record;
  state.mode = "animate";
  state.step = record.strokes.length;
  viewerTitle.textContent = `${record.character} / ${record.segment_count} 笔`;
  viewerSubtitle.textContent = `${sourceLabel || record.source_name} · 可播放拆解过程`;
  setResultNote(record.overlap_pixel_count ? `检测到 ${record.overlap_pixel_count} 个重叠像素` : "像素独占归属 · 按字形顺序回放");
  document.querySelectorAll(".mode-button").forEach((button) => button.classList.toggle("is-active", button.dataset.mode === "animate"));
  playButton.disabled = false;
  resetButton.disabled = false;
  prevButton.disabled = false;
  nextButton.disabled = true;
  renderStage();
  renderLegend();
  setStep(record.strokes.length);
}

async function loadExample(id, button) {
  markActiveExample(button);
  setResultNote("正在加载示例…");
  try {
    const record = await getJson(`/api/examples/${encodeURIComponent(id)}`);
    loadRecord(record, "已有算法结果");
  } catch (error) {
    setResultNote(error.message, true);
  }
}

async function uploadImage(file) {
  if (!file) return;
  const formData = new FormData();
  formData.append("image", file);
  uploadZone.classList.add("is-uploading");
  setResultNote("正在调用拆笔画程序分析图片…");
  try {
    const record = await getJson("/api/analyze", { method: "POST", body: formData });
    document.querySelectorAll(".example-button").forEach((item) => item.classList.remove("is-active"));
    loadRecord(record, "刚刚上传");
  } catch (error) {
    setResultNote(error.message, true);
  } finally {
    uploadZone.classList.remove("is-uploading");
    imageInput.value = "";
  }
}

document.querySelectorAll(".mode-button").forEach((button) => button.addEventListener("click", () => setMode(button.dataset.mode)));
playButton.addEventListener("click", () => (state.playing ? stopPlayback() : startPlayback()));
resetButton.addEventListener("click", () => { stopPlayback(); setStep(0); });
prevButton.addEventListener("click", () => setStep(state.step - 1));
nextButton.addEventListener("click", () => setStep(state.step + 1));
speedInput.addEventListener("input", () => {
  state.speed = Number(speedInput.value);
  speedValue.value = `${(state.speed / 1000).toFixed(2)}s`;
  speedValue.textContent = `${(state.speed / 1000).toFixed(2)}s`;
  if (state.playing) startPlayback();
});
imageInput.addEventListener("change", () => uploadImage(imageInput.files[0]));
["dragenter", "dragover"].forEach((eventName) => uploadZone.addEventListener(eventName, (event) => { event.preventDefault(); uploadZone.classList.add("is-dragging"); }));
["dragleave", "drop"].forEach((eventName) => uploadZone.addEventListener(eventName, (event) => { event.preventDefault(); uploadZone.classList.remove("is-dragging"); }));
uploadZone.addEventListener("drop", (event) => uploadImage(event.dataTransfer.files[0]));

async function init() {
  try {
    const payload = await getJson("/api/examples");
    state.examples = payload.examples;
    exampleCount.textContent = `${state.examples.length} 个`;
    exampleTotal.textContent = state.examples.length;
    renderExampleList();
    if (state.examples[0]) {
      const firstButton = exampleList.querySelector(".example-button");
      await loadExample(state.examples[0].id, firstButton);
    }
  } catch (error) {
    exampleList.innerHTML = `<p class="loading-line">无法连接本地服务：${error.message}</p>`;
    setResultNote("请确认已用 python server.py 启动网站", true);
  }
}

init();
