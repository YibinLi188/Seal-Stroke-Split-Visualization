(() => {
  function sum(values) {
    return values.reduce((total, value) => total + value, 0);
  }

  function sequenceDistance(left, right) {
    const leftTotal = sum(left);
    const rightTotal = sum(right);
    const width = Math.max(left.length, right.length);
    let distance = Math.abs(left.length - right.length) * 0.28;

    for (let index = 0; index < width; index += 1) {
      const leftValue = left[index] ? left[index] / leftTotal : 0;
      const rightValue = right[index] ? right[index] / rightTotal : 0;
      distance += Math.abs(leftValue - rightValue);
    }
    return distance;
  }

  function describeRelation(glyph, candidate, distance) {
    if (glyph.metrics.lengths.join(",") === candidate.metrics.lengths.join(",")) {
      return { type: "sequence", label: "序列一致", score: 100 };
    }
    if (glyph.metrics.segmentCount === candidate.metrics.segmentCount) {
      return { type: "segments", label: `同为 ${glyph.metrics.segmentCount} 段`, score: 76 - distance * 28 };
    }
    return { type: "segments", label: "段数接近", score: 58 - distance * 24 };
  }

  function relatedGlyphs(glyphs, glyph, limit = 6) {
    return glyphs
      .filter((candidate) => candidate.id !== glyph.id)
      .map((candidate) => {
        const segmentGap = Math.abs(candidate.metrics.segmentCount - glyph.metrics.segmentCount);
        const distance = sequenceDistance(glyph.metrics.lengths, candidate.metrics.lengths);
        const relation = describeRelation(glyph, candidate, distance);
        const score = relation.score - segmentGap * 11 - Math.abs(candidate.metrics.overlapPixels - glyph.metrics.overlapPixels) / 20;
        return { glyph: candidate, ...relation, distance, score };
      })
      .filter((entry) => entry.score > 10)
      .sort((left, right) => right.score - left.score)
      .slice(0, limit);
  }

  function filterRelations(relations, filter) {
    if (filter === "all") return relations;
    return relations.filter((relation) => relation.type === filter);
  }

  window.RelationEngine = { relatedGlyphs, filterRelations };
})();
