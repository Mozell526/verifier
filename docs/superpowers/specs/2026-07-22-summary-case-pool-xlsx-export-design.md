# 候选区表格 XLSX 导出设计

## 背景

`impl/frontend/summary.html` 的“用例池候选区”展示候选用例及其最新批量运行结果。页面当前最多渲染筛选结果的前 100 行，但批量候选区可以包含更多数据。左侧现有“导出已选”只会把选中的 VNext MockCase JSON 回填到文本框，并不会下载文件，也不会包含候选表中的 Judge、Attribute 等运行结果。

本变更新增真正的 Excel 下载能力。V1 只导出当前 Scenario 和达成状态筛选命中的全部行，生成 `.xlsx` 文件，不导出 Trace。

## 目标

- 在浏览器内直接生成并下载候选区 `.xlsx` 文件，不新增后端接口。
- 导出当前筛选命中的全部行，不受页面 100 行渲染上限影响。
- 导出与页面相同的数据来源和业务口径，但不继承页面字符截断。
- 同时提供人类可读的 Judge/Attribute 摘要和完整 Judge/Attribute JSON。
- 保持原有 MockCase JSON 回填能力及其他候选区行为不变。

## 非目标

- V1 不导出 Trace，也不提供 Trace 导出开关。后续可以扩展为显式选项。
- 不支持 CSV、多个工作表、服务端生成、模板导出或后台导出任务。
- 不重构批量归因、候选区持久化、结果合并或用例池库。
- 不为大规模导出引入 Web Worker；当前正式 Mock 数据集加载上限为 500 条。

## 已选方案

采用本地托管的 ExcelJS 4.4.0 浏览器包。将固定版本的浏览器构建放在 `impl/frontend/vendor/exceljs.min.js`，并保留对应许可证文件。`impl/frontend/` 已由服务作为静态目录发布，因此无需改变后端路由。页面运行时不访问 CDN。

选择该方案的原因是 ExcelJS 能在纯浏览器环境生成 `.xlsx`，并支持本功能需要的列宽、自动换行、冻结表头、自动筛选和基础样式。

### 未选方案

1. **CDN 加载 ExcelJS**：集成改动较小，但本地或内网环境会依赖外部网络，CDN 不可用时导出失效。
2. **前端自行实现 OOXML**：无需第三方依赖，但需要维护 XML、关系文件和 ZIP 打包，复杂度及损坏文件风险不符合本功能范围。
3. **后端内存生成并流式返回**：不必落盘，但前端已有全部待导出数据，再传回后端会增加接口、传输和大请求处理成本。

## 用户交互

### 导出入口

在“用例池候选区”标题栏右侧、Scenario 和达成状态筛选器之后增加按钮：

`导出当前筛选 (.xlsx)`

按钮位置表明导出范围受当前两个筛选器控制。候选区标题附近显示总数和当前筛选命中数量，帮助用户在下载前确认范围。

左侧原“导出已选”按钮改名为“生成已选 JSON”，保持其回填已选 MockCase JSON 的行为不变，避免与 Excel 下载入口混淆。

### 反馈状态

- 当前筛选为 0 条时不下载，提示“当前筛选没有可导出用例”。
- 生成期间禁用按钮并显示“正在导出…”，防止重复触发。
- 成功后恢复按钮并提示导出条数及文件名。
- 失败时恢复按钮并显示可理解的错误信息，不产生损坏下载。

## 数据范围与一致性

页面增加 `currentFilteredCaseViews()`，集中实现当前 Scenario 和达成状态筛选：

1. 遍历完整 `casePool`，而不是已切片的页面行。
2. 对每一项调用现有 `caseView()`，通过 `request_key` 合并 `caseResults` 中的最新运行结果。
3. 使用与页面相同的 `fulfillmentStatus()` 和 `inferCaseScenario()` 判断筛选命中。
4. `renderCasePool()` 与 Excel 导出共同使用该函数，防止两套筛选逻辑漂移。
5. 页面仍只对返回结果执行 `slice(0, 100)`；导出不切片。

导出必须读取当前内存中的运行结果，不能从 `lightCasePool()` 或浏览器轻量持久化数据重建，否则会遗漏 Judge、Attribute 或刚完成的批量结果。

## 工作表结构

工作簿包含一个名为“用例池候选区”的工作表，列顺序固定为：

| 列 | 数据来源与格式 |
|---|---|
| ID | `tableRow(view).id`，缺失时回退源候选 ID |
| 来源 | 源候选的 `source` |
| 执行模式 | 与 `runModeLabel(view)` 相同的 mode/source 组合 |
| Scenario | `inferCaseScenario(view)` |
| Input / Live Request | `caseInputPayload(view)`，即当前 Trace input 或源 `live_request` |
| Output / 被评估输出 | `caseView()` 合并后的 `output` |
| Reference | `caseReference(view)` |
| 状态 | running/error 优先，否则使用 fulfillment 状态；存在行错误时附带错误文本 |
| Judge 摘要 | 页面 Judge 摘要的纯文本等价表示，不截断 reason |
| Judge JSON | 当前运行的完整 `judge` 对象 |
| 归因摘要 | 页面归因摘要的纯文本等价表示，不截断 summary text |
| Attribute JSON | 当前运行的完整 `attribute` 对象 |

不包含“选择”和 Trace 列。

对象和数组使用两空格缩进的 JSON 文本；字符串、数字和布尔值保留可读文本形式。Input、Output、Reference、Judge JSON、Attribute JSON 不使用 `formatJsonCell()` 或 `shortText()` 的页面字符限制。缺少评估或归因结果时，摘要分别写“尚未评估”和“尚未归因”，对应 JSON 单元格留空。

所有导出内容都作为字符串值写入，不创建公式对象，避免用户输入被解释为 Excel 公式。

## Excel 生成组件

新增 `impl/frontend/case_pool_export.js`，通过全局 `CasePoolExporter` 暴露一个窄接口：接收项目 ID、已扁平化的行数据和导出时间，生成并下载工作簿。该文件不读取 `casePool`、筛选器或其他页面 DOM 业务状态。

`summary.html` 负责：

- 调用 `currentFilteredCaseViews()`；
- 将业务对象映射为 12 列扁平数据；
- 管理导出按钮及页面反馈；
- 调用 `CasePoolExporter`。

`case_pool_export.js` 负责：

- 创建工作簿和“用例池候选区”工作表；
- 写入表头及数据；
- 处理单元格长度上限；
- 应用工作表样式；
- 生成 Blob、创建临时下载链接并及时释放 URL。

脚本加载顺序为 ExcelJS 浏览器包、`case_pool_export.js`、`summary.html` 现有页面脚本。若 ExcelJS 未成功加载，导出函数立即报出明确错误。

## Excel 格式

- 冻结首行。
- 首行开启自动筛选。
- 表头使用加粗字体和浅色背景。
- 全部数据单元格顶部对齐并自动换行。
- ID、来源、执行模式、Scenario、状态采用较窄列宽。
- Input、Output、Reference、摘要和完整 JSON 采用较宽列宽。
- 不增加复杂配色、合并单元格、图片、图表或额外元数据工作表。

文件名格式为：

`verifier-<project>-cases-<YYYYMMDD-HHmmss>.xlsx`

项目 ID 中不适合文件名的字符替换为连字符。

## Excel 单元格上限

Excel 单元格最多容纳 32,767 个字符。导出器在写入前检查每个字符串：

- 未超过上限时完整写入。
- 超过上限时保留尽可能多的前缀，并追加“[已因 Excel 单元格 32767 字符上限截断]”。
- 标记包含在 32,767 字符总长度内。
- 一个单元格超限不会阻止其他行生成。

V1 不拆分续列或额外工作表。若后续必须无损导出超大 Trace 或 JSON，应另行设计附件工作表或 JSON 压缩包。

## 错误处理

- **无匹配行**：不创建工作簿，页面提示当前筛选无结果。
- **依赖缺失**：检测不到 ExcelJS 时终止并提示本地导出组件未加载。
- **生成失败**：捕获异常、恢复按钮、显示错误，不留下临时链接。
- **重复点击**：导出 Promise 未完成前按钮保持禁用。
- **单元格超长**：按上限规则局部截断，不中止整个文件。

## 测试与验收

### 自动测试

1. 构造超过 100 条候选数据，验证页面只渲染前 100 条而导出包含全部筛选命中行。
2. 分别验证 Scenario、状态及组合筛选，导出条数与 `currentFilteredCaseViews()` 一致。
3. 验证 12 列名称、顺序和映射，且不存在“选择”及 Trace 列。
4. 验证 Input、Output、Reference 使用完整值，不继承页面截断。
5. 验证 Judge/Attribute 同时包含无截断摘要和完整 JSON。
6. 验证 32,767 字符边界、超长标记及生成文件可重新读取。
7. 验证 0 行、ExcelJS 缺失及生成异常不会触发损坏下载，按钮最终恢复。
8. 验证项目名清洗、时间戳和 `.xlsx` 文件名。
9. 验证“生成已选 JSON”仍调用原有已选 MockCase 回填逻辑。

### 浏览器与文件验收

1. 在 summary 页面应用 Scenario 和状态筛选后触发下载，确认浏览器获得预期文件名。
2. 使用 Excel 或 LibreOffice 打开文件，确认文件无修复警告。
3. 检查冻结表头、筛选器、列宽、自动换行和 JSON 换行格式。
4. 检查 pending、fulfilled、not_fulfilled、not_evaluable、running、error 行的导出语义。
5. 回归批量归因、候选区持久化、结果合并和 JSON 回填功能。

## 后续扩展

后续如需 Trace，可在导出入口增加显式选项，并单独决定导出完整 Trace、Trace 摘要或附件工作表。该扩展不得改变 V1 默认不导出 Trace 的行为。
