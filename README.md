# 古文字结构互动系统

一个面向小篆字形研究的小型协作网站。它把图像算法生成的候选笔段、人工校释、字形相似度与关系浏览放在同一处，适合团队逐步累积资料。

当前已导入 `v1/拆笔画/outputs/experiment_v1` 的 17 个样本。自动拆解是研究线索，不应直接视为已确认的文字学结论。

## 使用

直接打开 `index.html` 即可浏览；不需要安装依赖。上传 GitHub 后，在仓库设置中启用 GitHub Pages，选择从默认分支根目录发布即可。

页面支持：

- 搜索和选择古文字字形
- 切换原始图、笔段合成图、总览图、骨架图与检查图
- 单独查看每一个候选笔段
- 查看释义、材料来源、构形说明和人工核对状态
- 按笔段数量、长度序列、重叠情况浏览相似字形和关系图

## 团队如何更新

1. 把新的实验输出目录准备为与 `experiment_v1` 相同的结构。
2. 在 `data/glyph-notes.json` 补充或修改人工资料：释义、构形、部件、核对状态。
3. 执行导入命令（示例为新实验 `v2`）：

```powershell
python .\scripts\import_experiment.py --experiment ..\v2\outputs\experiment_v2 --source-images ..\v2\data\小篆例 --version v2
```

4. 检查页面后提交以下变化：`data/glyphs.js`、`data/glyph-notes.json`、`public/assets/` 和有改动的界面文件。

首次导入 `v1` 的默认命令：

```powershell
python .\scripts\import_experiment.py
```

## 项目结构

```text
index.html                  页面结构
styles.css                  响应式界面样式
data/glyph-notes.json       团队人工校释资料，可直接编辑
data/glyphs.js              由导入脚本生成的浏览数据
public/assets/              需要随仓库发布的原图与实验图
scripts/import_experiment.py 实验输出导入器
src/relation-engine.js      字形相似度和候选关系规则
src/graph-renderer.js       关系图渲染与节点交互
src/ui.js                   目录、详情、笔段等界面渲染
src/app.js                  页面状态与模块协调
```

更具体的分工边界见 `ARCHITECTURE.md`，资料录入约定见 `CONTRIBUTING.md`。
