# ECharts 配置审查清单

> 配套 skill：website-qa-gates ｜ references ｜ 2026-10-06（VIZ7 新增，追加式补入）
> 适用：任何含 ECharts 图表的网站变更发布前的机械审查（CI/发布前 run，可人工＋源码 grep）。

## E1 · option 配置可读性

- 做什么：检查图表 option 是否写成可审查的结构（命名 series、显式 title/text、legend data 与 series 对应）。
- 方法：源码 grep `echarts.init` ＋逐项审读 option 对象。
- PASS 标准：无匿名魔法数字（数字配注释或常量）、axis/legend/tooltip 配置显式、不依赖 ECharts 默认配色。

## E2 · 禁止误导性轴配置

- 做什么：查 y 轴起点截断、双轴比例悬殊、柱条宽度夸张等视觉误导。
- 方法：审查 option 中 `yAxis.min` / `yAxis.max` / 双 `yAxis` / `barWidth`。
- PASS 标准：数值轴默认从 0 起；yAxis.min 非 0 必须经图表评审人书面批准并在图注注明；双轴时两侧轴单位/量级必须在图注写明，不许用双轴制造"赶超"假象。

## E3 · 数据-渲染一致性

- 做什么：option 里的 series.data 必须与来源数据（API/JSON/静态数据源）一致，变更后联动改全处。
- 方法：grep 数据来源字段与 option 字段名交叉比对；变更联动数字复核。
- PASS 标准：数据断言与数据源一一对应；数字联动零漂移（G6 机械项同标准）。

## E4 · tooltip/标注完整性

- 做什么：tooltip 必须给出可解释的值（数值＋单位＋口径），标注必须说明统计口径（如"同比""演示数据"）。
- PASS 标准：tooltip formatter 含单位与口径；图内任何大字数字配口径小字（见 data-honesty-checklist.md H2）。

## E5 · 性能基线

- 做什么：防止大数据量图表拖慢首屏。
- PASS 标准：数据点 >1000 时开 `large` 模式或采样；单页图表初始化总耗时 <300ms（真机实测）；图表初始化不得阻塞 LCP（异步 init 或 defer）。

## E6 · 销毁与重渲染

- 做什么：SPA/hash 路由切换时图表实例必须 dispose，防止内存泄漏与残影。
- PASS 标准：路由切换/语言切换后复查 `echarts.getInstanceByDom` 无残留实例；切换 10 次无内存持续增长（DevTools heap 快照）。

## 证据要求

- E1–E4：贴 option 关键片段＋逐项 PASS/FAIL。
- E5–E6：贴真机实测命令与输出摘要。
- 任一 FAIL 停发，按 A-011 三段制（结论＋证据＋怎么修）输出。
