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
  };

  function selectedGlyph() {
    return glyphById.get(state.selectedId);
  }

  function selectGlyph(id) {
    if (!glyphById.has(id)) return;
    state.selectedId = id;
    state.selectedView = "original";
    state.selectedSegment = null;
    render();
  }

  function setView(view, segment) {
    state.selectedView = view;
    state.selectedSegment = segment;
    render();
  }

  function render() {
    const glyph = selectedGlyph();
    const allRelations = window.RelationEngine.relatedGlyphs(glyphs, glyph);
    const relations = window.RelationEngine.filterRelations(allRelations, state.relationFilter);
    window.GlyphUI.renderCatalog(glyphs, state.selectedId, state.query, state.catalogFilter, selectGlyph);
    window.GlyphUI.renderTabs(glyph, state.selectedView, state.selectedSegment, setView);
    window.GlyphUI.renderImage(glyph, state.selectedView, state.selectedSegment);
    window.GlyphUI.renderMetrics(glyph);
    window.GlyphUI.renderSegments(glyph, state.selectedSegment, (segment) => setView("segment", segment));
    window.GlyphUI.renderRecord(glyph);
    window.GlyphUI.renderSimilar(relations, selectGlyph);
    window.GraphRenderer.render(document.querySelector("#relationGraph"), glyph, relations, selectGlyph);
    document.querySelector("#graphSummary").textContent = relations.length
      ? `当前展示 ${relations.length} 个候选关系。关系由笔段数量、长度序列与重叠情况自动推断，供人工核对。`
      : "当前筛选下暂无候选关系。可切换关系筛选或补充人工关系数据。";
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

  window.GlyphUI.renderDatasetStatus(dataset);
  render();
})();
