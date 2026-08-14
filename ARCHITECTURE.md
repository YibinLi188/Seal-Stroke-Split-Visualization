# 协作架构

这个项目借鉴了 Laddergraph Visualization 的核心做法：将数据、计算、图形渲染和界面状态分离，使多人可以围绕清晰边界协作。

## 分层

- `data/glyph-notes.json`：人工知识层。只放可追溯的释义、部件、构形与审核状态；不要把自动算法结果手工复制到这里。
- `scripts/import_experiment.py`：实验导入层。读取一版算法输出、复制发布所需图片，并生成 `data/glyphs.js`。
- `src/relation-engine.js`：关系规则层。不访问页面元素；只计算候选相似字形及其理由。
- `src/graph-renderer.js`：图形视图层。只将关系数据绘制为 SVG，并向上层报告点击的节点。
- `src/ui.js`：界面视图层。只更新目录、详情、候选笔段和资料面板。
- `src/app.js`：薄控制器。保存当前选择、筛选状态，并协调上述模块。
- `index.html` / `styles.css`：页面结构与样式。

## 推荐分工

- 资料研究成员维护 `data/glyph-notes.json`，并在拉取请求中注明文献来源与核对日期。
- 算法成员维护实验工程，输出稳定的 `summary.json` 与每字 `result.json`，随后运行导入脚本。
- 前端成员维护 `src/ui.js`、`src/graph-renderer.js` 与 `styles.css`。
- 方法成员维护 `src/relation-engine.js`，每次调整相似关系规则时写明算法依据。

## 数据规则

- `data/glyphs.js` 是生成文件，不要直接手改。
- 自动拆解字段使用“候选笔段”“自动建议”等表述，避免与人工确认部件混淆。
- 一项人工释义或构形结论没有出处时，状态应保持“待校释”或“待核”。
- 需要添加人工确认的字间关系时，建议先扩展独立的 `data/manual-relations.json`，再在关系规则层合并；不要把关系硬写入页面代码。

## 检查

每次改动至少检查：

```powershell
node --check .\src\relation-engine.js
node --check .\src\graph-renderer.js
node --check .\src\ui.js
node --check .\src\app.js
```

然后直接打开 `index.html`，确认搜索、图层切换、笔段点击与关系图节点点击均可工作。
