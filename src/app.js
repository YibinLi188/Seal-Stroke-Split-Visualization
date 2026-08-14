(() => {
  const { dataset, glyphs } = window.GLYPH_DATA;
  const glyphById = new Map(glyphs.map((glyph) => [glyph.id, glyph]));
  const state = {
    selectedId: glyphs.find((glyph) => glyph.mark === "尚")?.id || glyphs[0].id,
    selectedView: "original",
    selectedSegment: null,
    query: "",
    catalogFilter: "all",
    relationFilter: "all",
    replayStep: 0,
    replayDelay: 800,
    isPlaying: false,
    replayTimer: null,
    replayFinished: false,
  };

  function selectedGlyph() {
    return glyphById.get(state.selectedId);
  }

  function selectGlyph(id) {
    if (!glyphById.has(id)) return;
    stopReplay();
    state.selectedId = id;
    state.selectedView = "original";
    state.selectedSegment = null;
    state.replayStep = 0;
    state.replayFinished = false;
    render();
  }

  function setView(view, segment) {
    if (view !== "replay") stopReplay();
    state.selectedView = view;
    state.selectedSegment = segment;
    render();
  }

  function stopReplay() {
    state.isPlaying = false;
    if (state.replayTimer) window.clearTimeout(state.replayTimer);
    state.replayTimer = null;
  }

  function scheduleReplay() {
    if (!state.isPlaying) return;
    state.replayTimer = window.setTimeout(() => {
      const glyph = selectedGlyph();
      if (state.replayStep < glyph.segments.length) {
        state.replayStep += 1;
      } else {
        state.isPlaying = false;
        state.replayFinished = true;
      }
      render();
      scheduleReplay();
    }, state.replayDelay);
  }

  function toggleReplay() {
    const glyph = selectedGlyph();
    if (state.isPlaying) {
      stopReplay();
      render();
      return;
    }
    state.selectedView = "replay";
    state.selectedSegment = null;
    if (state.replayStep >= glyph.segments.length) state.replayStep = 0;
    state.replayFinished = false;
    state.isPlaying = true;
    render();
    scheduleReplay();
  }

  function moveReplay(step) {
    stopReplay();
    state.selectedView = "replay";
    state.selectedSegment = null;
    state.replayStep = Math.max(0, Math.min(step, selectedGlyph().segments.length));
    state.replayFinished = state.replayStep >= selectedGlyph().segments.length;
    render();
  }

  function render() {
    const glyph = selectedGlyph();
    const allRelations = window.RelationEngine.relatedGlyphs(glyphs, glyph);
    const relations = window.RelationEngine.filterRelations(allRelations, state.relationFilter);
    window.GlyphUI.renderCatalog(glyphs, state.selectedId, state.query, state.catalogFilter, selectGlyph);
    window.GlyphUI.renderTabs(glyph, state.selectedView, state.selectedSegment, setView);
    window.GlyphUI.renderImage(glyph, state.selectedView, state.selectedSegment, state.replayStep, state.replayFinished);
    window.GlyphUI.renderPlaybackControls(glyph, state.selectedView, state.replayStep, state.isPlaying, state.replayDelay);
    window.GlyphUI.renderMetrics(glyph);
    window.GlyphUI.renderSegments(glyph, state.selectedSegment, (segment) => setView("segment", segment));
    window.GlyphUI.renderRecord(glyph);
    window.GlyphUI.renderSimilar(relations, selectGlyph);
    window.GraphRenderer.render(document.querySelector("#relationGraph"), glyph, relations, selectGlyph);
    document.querySelector("#graphSummary").textContent = relations.length
      ? `当前展示 ${relations.length} 个可能相近的字形，供观察和讨论。`
      : "当前筛选下暂未找到相近字形。可切换筛选方式再看看。";
  }

  document.querySelector("#glyphSearch").addEventListener("input", (event) => {
    state.query = event.target.value;
    window.GlyphUI.renderCatalog(glyphs, state.selectedId, state.query, state.catalogFilter, selectGlyph);
  });
  document.querySelector("#catalogFilter").addEventListener("change", (event) => {
    state.catalogFilter = event.target.value;
    window.GlyphUI.renderCatalog(glyphs, state.selectedId, state.query, state.catalogFilter, selectGlyph);
  });
  document.querySelector("#relationFilter").addEventListener("change", (event) => {
    state.relationFilter = event.target.value;
    render();
  });
  document.querySelector("#replayPlay").addEventListener("click", toggleReplay);
  document.querySelector("#replayReset").addEventListener("click", () => moveReplay(0));
  document.querySelector("#replayPrevious").addEventListener("click", () => moveReplay(state.replayStep - 1));
  document.querySelector("#replayNext").addEventListener("click", () => moveReplay(state.replayStep + 1));
  document.querySelector("#replaySpeed").addEventListener("change", (event) => {
    state.replayDelay = Number(event.target.value);
    if (state.isPlaying) {
      stopReplay();
      state.isPlaying = true;
      scheduleReplay();
    }
    render();
  });

  window.GlyphUI.renderDatasetStatus(dataset);
  render();
})();
