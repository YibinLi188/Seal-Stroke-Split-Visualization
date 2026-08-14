(() => {
  const VIEW_MODES = [
    ["original", "原始字形", "原始输入图像"],
    ["composite", "笔段合成", "自动拆解的彩色笔段"],
    ["gallery", "笔段总览", "全部候选笔段"],
    ["binary", "二值图", "二值化后的字形"],
    ["skeleton", "骨架", "单像素骨架"],
    ["overlay", "叠加检查", "候选笔段与字形叠加"],
    ["overlap", "重叠检查", "笔段重叠区域"],
  ];

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
        <span class="glyph-item-copy"><strong>${escapeHtml(glyph.title)}</strong><small>${glyph.metrics.segmentCount} 个候选笔段</small></span>
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

  function renderImage(glyph, selectedView, selectedSegment) {
    const image = document.querySelector("#glyphImage");
    const caption = document.querySelector("#imageCaption");
    if (selectedSegment) {
      image.src = selectedSegment.image;
      image.alt = `${glyph.title} 的第 ${selectedSegment.id} 个候选笔段`;
      caption.textContent = `第 ${selectedSegment.id} 个候选笔段`;
      return;
    }
    const view = VIEW_MODES.find(([key]) => key === selectedView) || VIEW_MODES[0];
    image.src = glyph.assets[view[0]];
    image.alt = `${glyph.title}：${view[1]}`;
    caption.textContent = view[2];
  }

  function renderMetrics(glyph) {
    const metrics = [
      ["候选笔段", `${glyph.metrics.segmentCount} 段`],
      ["骨架长度", `${glyph.metrics.lengths.reduce((total, value) => total + value, 0)} 点`],
      ["重叠像素", `${glyph.metrics.overlapPixels} px`],
      ["实验版本", glyph.source.experiment],
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
        <span class="segment-copy"><strong>第 ${segment.id} 个笔段</strong><small>骨架点数 ${segment.pointCount}${segment.pixelCount ? ` · 像素 ${segment.pixelCount}` : ""}</small></span>`;
      button.addEventListener("click", () => onSelect(segment));
      container.append(button);
    });
  }

  function renderRecord(glyph) {
    setText("#glyphSource", `${glyph.source.collection} · ${glyph.source.section}`);
    setText("#glyphTitle", glyph.title);
    setText("#glyphUnicode", glyph.unicode);
    setText("#reviewStatus", glyph.reviewStatus);
    setText("#glyphDefinition", glyph.definition);
    setText("#formationNote", glyph.formation);
    document.querySelector("#sourceDetails").innerHTML = [
      ["材料", glyph.source.collection],
      ["分部", glyph.source.section],
      ["样本", glyph.source.originalFile],
      ["实验", glyph.source.experiment],
    ].map(([term, definition]) => `<div><dt>${escapeHtml(term)}</dt><dd>${escapeHtml(definition)}</dd></div>`).join("");

    const components = document.querySelector("#componentList");
    if (!glyph.components.length) {
      components.innerHTML = '<p class="empty-state compact">尚未登记人工部件。可先以“候选笔段”观察字形，再由团队补充构形标签。</p>';
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
    setText("#datasetStatus", `${dataset.version} 实验 · ${dataset.count} 个字形样本`);
    setText("#glyphCount", `${dataset.count} 个`);
  }

  window.GlyphUI = {
    renderCatalog,
    renderTabs,
    renderImage,
    renderMetrics,
    renderSegments,
    renderRecord,
    renderSimilar,
    renderDatasetStatus,
  };
})();
