(() => {
  const VIEW_MODES = [
    ["original", "原字", "观察原始字形"],
    ["replay", "逐笔书写", "按顺序观看字形写成"],
    ["composite", "笔画拆解", "观察字形由哪些笔画组成"],
  ];
  const SVG_NS = "http://www.w3.org/2000/svg";

  function svgElement(tag, attributes = {}) {
    const element = document.createElementNS(SVG_NS, tag);
    Object.entries(attributes).forEach(([name, value]) => element.setAttribute(name, value));
    return element;
  }

  function strokePath(points) {
    return (points || [])
      .filter((point) => Array.isArray(point) && point.length >= 2)
      .map(([y, x], index) => `${index ? "L" : "M"} ${Number(x)} ${Number(y)}`)
      .join(" ");
  }

  function revealWidth(segment) {
    const points = Math.max(1, segment.pointCount || segment.points?.length || 1);
    const pixels = Math.max(1, segment.pixelCount || points);
    return Math.max(1.4, Math.min(5, (pixels / points) * 1.05));
  }

  function animateMaskPath(path) {
    requestAnimationFrame(() => {
      const length = path.getTotalLength();
      if (!Number.isFinite(length) || length <= 0) return;
      path.style.strokeDasharray = `${length} ${length}`;
      path.style.strokeDashoffset = `${length}`;
      path.style.transition = "stroke-dashoffset 360ms linear";
      requestAnimationFrame(() => { path.style.strokeDashoffset = "0"; });
    });
  }

  const escapeHtml = (value) => String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

  function setText(id, value) {
    document.querySelector(id).textContent = value;
  }

  function renderCatalog(glyphs, selectedId, query, filter, onSelect) {
    const normalizedQuery = query.trim().toLowerCase();
    const filtered = glyphs.filter((glyph) => {
      const searchable = [glyph.mark, glyph.title, glyph.sourceId, glyph.source.section, glyph.reviewStatus].join(" ").toLowerCase();
      const matchQuery = !normalizedQuery || searchable.includes(normalizedQuery);
      const segments = glyph.metrics.segmentCount;
      const matchFilter = filter === "all"
        || (filter === "review" && glyph.reviewStatus.includes("待"))
        || (filter === "two-to-four" && segments >= 2 && segments <= 4)
        || (filter === "five-plus" && segments >= 5);
      return matchQuery && matchFilter;
    });
    const container = document.querySelector("#glyphList");
    container.replaceChildren();
    filtered.forEach((glyph) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `glyph-item${glyph.id === selectedId ? " is-active" : ""}`;
      button.innerHTML = `
        <span class="glyph-item-mark">${escapeHtml(glyph.mark)}</span>
        <span class="glyph-item-copy"><strong>${escapeHtml(glyph.title)}</strong><small>${glyph.metrics.segmentCount} 笔</small></span>
        <span class="glyph-item-id">${escapeHtml(glyph.sourceId)}</span>`;
      button.addEventListener("click", () => onSelect(glyph.id));
      container.append(button);
    });
    if (!filtered.length) {
      container.innerHTML = '<p class="empty-state">没有匹配的字形。</p>';
    }
  }

  function renderTabs(glyph, selectedView, selectedSegment, onViewChange) {
    const container = document.querySelector("#viewTabs");
    container.replaceChildren();
    VIEW_MODES.forEach(([key, label, description]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.role = "tab";
      button.className = `view-tab${selectedView === key && !selectedSegment ? " is-active" : ""}`;
      button.textContent = label;
      button.title = description;
      button.addEventListener("click", () => onViewChange(key, null));
      container.append(button);
    });
  }

  function renderImage(glyph, selectedView, selectedSegment, replayStep, replayFinished) {
    const image = document.querySelector("#glyphImage");
    const replayCanvas = document.querySelector("#replayCanvas");
    const caption = document.querySelector("#imageCaption");
    const isReplay = selectedView === "replay" && !selectedSegment;
    image.hidden = isReplay;
    replayCanvas.hidden = !isReplay;

    if (isReplay) {
      replayCanvas.replaceChildren();
      const width = glyph.canvas?.width || 80;
      const height = glyph.canvas?.height || 80;
      const svg = svgElement("svg", {
        viewBox: `0 0 ${width} ${height}`,
        preserveAspectRatio: "xMidYMid meet",
        role: "img",
        "aria-label": `${glyph.title} 的逐笔书写过程`,
      });
      const original = encodeURI(glyph.assets.original);
      const ghost = svgElement("image", { href: original, x: 0, y: 0, width, height, opacity: "0.1" });
      svg.append(ghost);

      if (replayFinished) {
        svg.append(svgElement("image", { href: original, x: 0, y: 0, width, height }));
        caption.textContent = "已完成书写，恢复为原始字形";
      } else {
        const maskId = `replay-mask-${glyph.sourceId}`;
        const defs = svgElement("defs");
        const mask = svgElement("mask", {
          id: maskId,
          x: 0,
          y: 0,
          width,
          height,
          maskUnits: "userSpaceOnUse",
          maskContentUnits: "userSpaceOnUse",
        });
        mask.append(svgElement("rect", { x: 0, y: 0, width, height, fill: "black" }));
        glyph.segments.slice(0, replayStep).forEach((segment, index) => {
          const pathData = strokePath(segment.points);
          if (!pathData) return;
          const path = svgElement("path", {
            d: pathData,
            fill: "none",
            stroke: "white",
            "stroke-width": revealWidth(segment),
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
          });
          mask.append(path);
          if (index === replayStep - 1) animateMaskPath(path);
        });
        defs.append(mask);
        svg.append(defs, svgElement("image", {
          href: original,
          x: 0,
          y: 0,
          width,
          height,
          mask: `url(#${maskId})`,
        }));
        caption.textContent = replayStep
          ? `正在书写第 ${replayStep} 笔`
          : "从第一笔开始书写";
      }
      replayCanvas.append(svg);
      return;
    }

    if (selectedSegment) {
      image.src = selectedSegment.image;
      image.alt = `${glyph.title} 的第 ${selectedSegment.id} 笔`;
      caption.textContent = `第 ${selectedSegment.id} 笔`;
      return;
    }
    const view = VIEW_MODES.find(([key]) => key === selectedView) || VIEW_MODES[0];
    image.src = glyph.assets[view[0]];
    image.alt = `${glyph.title}：${view[1]}`;
    caption.textContent = view[2];
  }

  function renderPlaybackControls(glyph, selectedView, replayStep, isPlaying, replayDelay) {
    const controls = document.querySelector("#playbackControls");
    controls.hidden = selectedView !== "replay";
    if (controls.hidden) return;
    document.querySelector("#replayProgress").textContent = `${replayStep} / ${glyph.segments.length} 笔`;
    document.querySelector("#replayPlay").textContent = isPlaying ? "暂停" : "播放";
    document.querySelector("#replayPrevious").disabled = replayStep === 0;
    document.querySelector("#replayNext").disabled = replayStep >= glyph.segments.length;
    document.querySelector("#replaySpeed").value = String(replayDelay);
  }

  function renderMetrics(glyph) {
    const metrics = [
      ["笔画数量", `${glyph.metrics.segmentCount} 笔`],
      ["观察方式", "可逐笔观看"],
    ];
    document.querySelector("#metricStrip").innerHTML = metrics
      .map(([label, value]) => `<div><span>${label}</span><strong>${value}</strong></div>`)
      .join("");
  }

  function renderSegments(glyph, selectedSegment, onSelect) {
    const container = document.querySelector("#segmentsList");
    container.replaceChildren();
    glyph.segments.forEach((segment) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `segment-button${selectedSegment && selectedSegment.id === segment.id ? " is-active" : ""}`;
      button.innerHTML = `
        <span class="segment-thumb"><img src="${encodeURI(segment.image)}" alt="" /></span>
        <span class="segment-copy"><strong>第 ${segment.id} 笔</strong><small>点击查看这一笔</small></span>`;
      button.addEventListener("click", () => onSelect(segment));
      container.append(button);
    });
  }

  function renderRecord(glyph) {
    setText("#glyphSource", `${glyph.source.collection} · ${glyph.source.section}`);
    setText("#glyphTitle", glyph.title);
    setText("#glyphDefinition", glyph.definition);
    setText("#formationNote", glyph.formation.includes("待") ? "这部分结构说明仍在整理中。" : glyph.formation);
    document.querySelector("#sourceDetails").innerHTML = [
      ["材料", glyph.source.collection],
      ["分部", glyph.source.section],
    ].map(([term, definition]) => `<div><dt>${escapeHtml(term)}</dt><dd>${escapeHtml(definition)}</dd></div>`).join("");

    const components = document.querySelector("#componentList");
    if (!glyph.components.length) {
      components.innerHTML = '<p class="empty-state compact">这一字形的部件说明仍在整理中。</p>';
      return;
    }
    components.innerHTML = glyph.components.map((component) => `
      <div class="component-item"><strong>${escapeHtml(component.name)}</strong><span>${escapeHtml(component.kind)} · ${escapeHtml(component.status)}</span></div>`).join("");
  }

  function renderSimilar(relations, onSelect) {
    const container = document.querySelector("#similarList");
    container.replaceChildren();
    if (!relations.length) {
      container.innerHTML = '<p class="empty-state compact">当前筛选下没有足够接近的候选字形。</p>';
      return;
    }
    relations.forEach((relation) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "similar-item";
      button.innerHTML = `<span class="similar-mark">${escapeHtml(relation.glyph.mark)}</span><span><strong>${escapeHtml(relation.glyph.title)}</strong><small>${escapeHtml(relation.label)}</small></span><span class="similar-count">${relation.glyph.metrics.segmentCount} 段</span>`;
      button.addEventListener("click", () => onSelect(relation.glyph.id));
      container.append(button);
    });
  }

  function renderDatasetStatus(dataset) {
    setText("#datasetStatus", `${dataset.count} 个字形`);
    setText("#glyphCount", `${dataset.count} 个`);
  }

  window.GlyphUI = {
    renderCatalog,
    renderTabs,
    renderImage,
    renderPlaybackControls,
    renderMetrics,
    renderSegments,
    renderRecord,
    renderSimilar,
    renderDatasetStatus,
  };
})();
