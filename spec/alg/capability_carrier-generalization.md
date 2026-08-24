# 能力承载性协议通用化实施方案

关联：`capability_carrier.md`（协议）、`capability_carrier-reading.md`（读法）、
`capability_carrier-stability.md`（稳定性）。本文档是实施文档，落完后其结论回写协议文档。**已按本文落地**（协议层 / 结构化形态 / `capability_provider` / 装载期 fail-fast）。

## 0. 背景与目标

轴2 目前只在 client_search 上运行。协议（三态 + fail-closed + 审计）和一种实现
（field/operator/value 结构化能力空间 + LLM mapper + 确定性 resolve）焊在
`impl/core/capability_carrier.py` 同一套代码里，连协议文档 §3 的判断顺序
（维度→操作符→值）也是结构化实现的内部逻辑。

目标：**把轴2从"一种实现"升格为"一个合同"**。借 Live 协议已验证的分层
（`live_protocol.py`：协议层 @final 主流程 + 形态基类二选一 + live_schema 项目自声明、
协议只管校验），做三件事：

1. 半接入状态（开 scope 但没物料）从"每个 run 标 error"改为装载期一次性 fail-fast；
2. 协议层收敛为形态无关合同，现在这套结构化方案降级为第一个形态；
3. client_search 最终轴2效果零漂移（冻结 NF 金标 + placements 重放 diff 做等价门）。

## 1. 现状问题

| # | 问题 | 现状位置 | 危害 |
|---|---|---|---|
| P1 | 半接入状态运行期爆炸 | `load_capability_snapshot` 返回 `fields=None` → 每个 NF 期望产出 `CarrierError` → run 标 error | 失败反馈点太晚太散，产生成批脏 run |
| P2 | 单文件混四层 | `capability_carrier.py` 1600+ 行：协议合同、结构化实现、alias 启发式、报表渲染 | 协议和实现无法独立演进，新形态没有接入点 |
| P3 | client_search 域词硬编码在 core | `_aliases_for` 里 车牌/姓名/子女 特判、`^(?:保单|客户)?(?:本人)?的?` 前缀剥离 | 其他项目带着别人家的域词跑 |
| P4 | client_search 项目函数名被提拔成 core 隐式接口 | `load_capability_snapshot` / `_lexicon_from_spec` / `_spoken_from_spec` 按 `capability_snapshot` / `capability_lexicon` / `value_mappings` 这三个名字 getattr 摸项目 `live.py` | 这三个是 client_search 的项目内部函数（`value_mappings` 甚至是 judge 也在消费的既有共享资产，轴2只是借用），core 认名字 = 项目私货进了合同；且接入完整性要跑起来才知道（即 P1） |
| P5 | 协议文档混入实现规范 | `capability_carrier.md` §3 判断顺序是结构化形态内部逻辑 | 非结构化项目误以为"必须结构化可枚举才能上轴2" |

中文描述解析启发式（表示/如/例如/不表示）不算缺陷：它是"结构化形态 + 中文物料"
的约定，留在形态层，但要在形态规范里写明，且项目可用 manifest 显式 `aliases` 绕过。

## 2. 目标架构

对照 Live 协议四层（live_protocol.py 协议+操作层 / live.py 通用层 / projects/<id>/live.py 项目层）：

```text
协议层  impl/core/capability_carrier.py（瘦身后）
        拥有：三态/映射/主流程/审计/渲染/绑定。项目与形态不可改流程。
形态层  impl/core/capability_structured.py（新文件）
        结构化形态：manifest→snapshot、alias 提取、mapper、resolve、rescue、lexicon。
        未来的非结构化形态是它的平级兄弟，不是它的子类。
项目层  impl/projects/<id>/live.py
        声明 capability_provider（选形态 + 供物料），冻结资产，自动进 current_fingerprint。
```

### 2.1 协议层合同（形态无关，@final 拥有）

输入合同：
- 只接 NF blocking 期望（文本 + expectation_id）；判后 pass；
- 不看 live 输出、不看轴1 理由、不改写轴1（`attach_row_placements` 的 RuntimeError 检查保留）。

输出合同（`map_placement` 产物，`validate_placements` 审计）：
- `placement ∈ {做不了, 做错了, 说不清}`；
- 做不了必须资料自认（`recognition ∈ _CANNOT_RECOGNITIONS`）；
- 每条 placement 带可回溯 `citations`，引用必须落在该项目 provider 声明的引用空间内
  （现在 `validate_placements` 写死"必须在 fields catalog"，改为按 provider 声明校验）；
- 说不清必带 `gap_kind + missing_material`，且 `gap_kind ≠ 工具失败`；
- 同维度同快照幂等（审计项：same-dimension placement drift）。

形态接口（协议层定义的 ABC，对照 `RealServiceLive`/`ProvidedOutputLive` 的地位）：

```python
class CapabilityCarrierBase(ABC):
    @abstractmethod
    def verdict_for(self, expectation) -> CarrierVerdict | CarrierError: ...
    @abstractmethod
    def snapshot_revision(self) -> str: ...      # 进 placement 审计与去重
    @abstractmethod
    def citation_space(self) -> set[str] | None:  # validate_placements 校验引用用
    @typing_final
    def place(self, payload) -> dict: ...         # 即现 place_not_fulfilled_payload 主流程
```

`CarrierVerdict` / `CarrierError` / `map_placement` 是协议层资产（三态怎么来的形态自己管，
三态往 placement 怎么映射协议管）。缓存与去重的具体键（读法字段集合）留在形态层，
协议层只通过审计强制幂等这一性质。

### 2.2 形态层：结构化形态（现有全部逻辑，行为不变）

`capability_structured.py` 承接：snapshot 构建、alias/negative 提取（中文物料约定）、
catalog/lexicon prompt 与命中、mapper 调用与解析、`evaluate_reading`/`resolve_carrier`、
rescue、值/操作符规范化。类名 `CapabilityCarrier → StructuredCarrier`，不留别名。

**形态构造函数收数据，不收函数名**：

```python
StructuredCarrier(
    manifest,            # 必填：受治理字段目录（field → operators/enums/description/...）
    lexicon=None,        # 可选：受治理业务词表（term → field/status/evidence）
    spoken=None,         # 可选：口语值别名（field → 口语表达列表）
)
```

manifest/lexicon/spoken 是本形态定义的**数据形状**（在形态规范里定义 schema），
不是任何函数名约定。数据从哪来——YAML、source 配置、和 judge 共享的项目资产——
完全是项目 provider 工厂内部的事，core 与形态层一概不认识项目函数名。

"维度→操作符→值"的判断顺序、枚举反查、口径表 rescue，全部属于本形态的实现规范，
从协议文档 §3 迁出（见阶段三）。

### 2.3 项目层：provider 显式声明（唯一的项目层合同）

协议层认识的项目符号**只有一个**：`impl/projects/<id>/live.py` 的 `capability_provider`。

```python
# client_search/live.py —— 示意
def capability_provider(spec: ProjectSpec) -> CapabilityCarrierBase:
    return StructuredCarrier(
        manifest=capability_snapshot(spec),    # 项目内部函数，名字随项目便
        lexicon=capability_lexicon(spec),
        spoken=value_mappings(spec),           # 复用 judge 也在用的既有共享资产
    )
```

- `capability_snapshot` / `capability_lexicon` / `value_mappings` 降回 client_search 的
  项目内部函数：core 里按这三个名字 getattr 的探测链（`load_capability_snapshot` /
  `_lexicon_from_spec` / `_spoken_from_spec`、以及 `spec.capability_manifest` 钩子）全部删除；
  别的项目给自家 provider 喂数据时爱叫什么叫什么；
- 没 `capability_provider` = 未接入轴2。scope 也没开 → 干净跳过（现状不变）；
- scope 开了但函数缺失/抛错 → 装载期 fail-fast（见 §3 阶段二），不进运行期；
- 函数存在 → `bind_capability_carrier` 调它拿 carrier，共享缓存语义不变；
- 协议层消费方（如 draft review 的 placement 审计）需要引用空间时，
  走 `carrier.citation_space()`，不再直接调 `load_capability_snapshot`。

## 3. 实施阶段

三阶段严格顺序，每阶段独立可验收、独立可合入。

### 阶段一：纯分层拆分（行为零变化）

**1a. 文件拆分。** 函数归属：

| 留在 `capability_carrier.py`（协议层） | 迁往 `capability_structured.py`（形态层） |
|---|---|
| 三态/GAP/RECOG 常量、`PROCESS_FIELD` | `_STOP_ALIASES`、`_HEAD_NOUN` 等启发式常量与正则 |
| `CarrierError`、`CarrierVerdict`、`snapshot_id` | `CarrierReading`、`CatalogHit`、`_Mapper*` dataclass、`MapperExhausted` |
| `map_placement`、`place_not_fulfilled_payload` | `evaluate_reading`、`resolve_carrier`、`unmapped_verdict` |
| `CapabilityCarrierBase`（新 ABC，place 为 @final） | `catalog_prompt`/`lexicon_prompt`/`lexicon_hits`/`catalog_hits`/`build_catalog_index` |
| `attach_row_placements`、`bind_capability_carrier`、`reset_live_carriers`、`live_carrier_report` | `rescue_catalog_misses`、`_rescue_missing_values`、`_reading_from_*`、`_canonical_*` |
| `validate_placements`、`inbox_entries`、`render_inbox` | `parse_mapper_payload`、`call_mapper_llm`、`_MAPPER_SYSTEM` |
| `format_placement_cell`、`carrier_text`、`collect_report_errors`、`format_carrier_errors` | alias/negative 提取全家（`_aliases_for` 等）、`snapshot_from_capability_manifest`、`normalize_lexicon` |
|  | `StructuredCarrier`（原 `CapabilityCarrier`）、getattr 物料 loaders（暂随形态层迁移，阶段二整体删除） |

外部调用方（`pipeline.py`、`draft_role_review.py`、`run_iteration.py`、
`render_loop_comparison_table.py`、`table_view.py`/`frontend_view.py`）引用的都是协议层符号，
import 不变。`tests/test_capability_carrier.py` 里引用结构化内部符号的测试改 import。

**1b. 域词下沉。** `_aliases_for` 里的三处 client_search 特判
（号牌/车牌 → 车牌号系列、人名/客户姓名 → 姓名系列、儿子女儿 → 子女）
从 core 删除，等价内容写入 client_search 的 capability manifest `aliases`
（或 `capability_lexicon.yaml`，按字段归属就近）。
`^(?:保单|客户)?(?:本人)?的?` 前缀剥离与中文描述解析保留在形态层，
在形态规范中写明为"中文物料约定"。

**1c. 等价门（本阶段验收）：**
- 迁移前后对 client_search 构建 snapshot，逐字段 diff `aliases`/`negatives` 集合，必须相等；
- `test_client_search_axis2_frozen_nf` 冻结 NF 金标全绿；
- `tests/test_capability_carrier.py` 全量通过；
- 用最近一次 rerun 的 mapper 缓存 payload 重放确定性判定，placements 逐条 diff 为空。

### 阶段二：provider 合同显式化 + 装载期 fail-fast

**2a. 项目层。** client_search `live.py` 增加 `capability_provider`（§2.3），
在工厂内部把自家三个物料函数的产出喂给 `StructuredCarrier(manifest=…, lexicon=…, spoken=…)`。
core 里按项目函数名 getattr 的探测链（`load_capability_snapshot` / `_lexicon_from_spec` /
`_spoken_from_spec`、`spec.capability_manifest` 钩子）全部删除，不留兼容层；
`draft_role_review.py` 里对 `load_capability_snapshot` 的直接调用改走
`bind_capability_carrier(spec).citation_space()`。

**2b. 装载期检查。** 两个卡点：
- `config_check.py` 增加一项：`enabled_scopes` 含 `capability_carrier` 的项目，
  其 live 模块必须有可调用的 `capability_provider`。缺 → config check 直接报
  "轴2接入未完成：缺 capability_provider"；
- `bind_capability_carrier`：provider 缺失或构造抛错 → raise（带项目名与缺失物料的明确信息），
  不再返回一个 `fields=None` 的空壳 carrier 让运行期慢慢爆。

**2c. 运行期错误语义收敛。** 三种状态各归各位：

| 状态 | 行为 |
|---|---|
| scope 未开 | 完全跳过，与今天一致（`bind` 返回 None） |
| scope 开、provider 缺 | 装载期报错，run 不启动，不产生半错数据 |
| scope 开、provider 在、运行期故障（mapper 耗尽/物料解析异常） | per-expectation `CarrierError`，fail-closed，现状语义 |

**2d. 验收：**
- 未开 scope 项目（QA/demo 等）确定性面与现状一致（对照 `capability_carrier.md` §10）；
- 新增测试：开 scope 缺 provider → config check 报错 + bind raise；
- client_search 全链路（pipeline 单 case + draft loop 单 iteration）行为与阶段一末尾一致；
- 冻结 NF 金标全绿。

### 阶段三：协议文档与 skill 收口

- `capability_carrier.md`：§3 判断顺序中"维度→操作符→值"的细则迁出，第一章收敛为
  形态无关合同（三态定义、证据要求、反面清单不动——它们本来就是通用的）；
  第二章新增"形态"一节：形态接口、结构化形态定位、引用空间由 provider 声明；
- `capability_carrier-reading.md`：标注为结构化形态的读法规范，判断顺序细则落到这里；
- `.claude/skills/evals/SKILL.md`：项目接入主流程增加可选步骤"轴2接入"。
  通用步骤只讲 provider 合同，不出现任何形态物料的函数名：
  1. 接入判定（Step 0 阶段）：先问项目是否拥有自己的受治理能力空间（物料归属
     不在本项目 → 暂不接入）；有则选形态——协议形态无关，已实现形态现场发现，
     没有合适形态 → 暂不接入，明确记录（避免复现 P5 的误解：形态清单是现状，
     不是协议门槛）；
  2. 实现 provider（填 stub 阶段）：`live.py` 写 `capability_provider`，
     选定形态并喂足该形态要求的数据（数据 schema 见形态规范，取数方式项目自定）；
  3. 开 scope：`project.yaml` `enabled_scopes: [capability_carrier]`，过 config check；
  4. 建门（纳入回归阶段）：从真实 NF case 冻结项目自己的 NF 金标；
  5. 词表后置沉淀（结构化形态特有）：真实误判出现再加词，走 fingerprint 变更门。

## 4. 明确不做

- **不实现第二个形态。** 非结构化项目的承载性裁决拿什么当"资料自认"证据，
  需要真实项目驱动；本方案只把合同和形态拆开、把口子留对；
- 不改 Judge prompt / JudgeResult / 归因 / 轴1 计分；
- 不动 `authority.md` 与通用裁决通道；后四个实验 scope 维持现状；
- 不留旧符号别名、不留 getattr 兼容层、不做迁移期双轨。

## 5. 总验收与回归门

1. `test_client_search_axis2_frozen_nf` 冻结 NF 金标：三个阶段每步全绿；
2. snapshot 等价：阶段一迁移前后 client_search snapshot 的 fields/aliases/negatives 逐项相等；
3. placements 重放 diff：用 rerun mapper 缓存 payload 重放，逐条 placement 无变化；
4. 未开 scope 项目：system prompt 快照、工具暴露列表、配置解析结果与现状一致；
5. 半接入状态：config check 报错文案指明缺什么、在哪补；
6. `tests/test_capability_carrier.py` 全量 + 相关调用方测试（pipeline/draft loop）通过。

## 6. 改动文件清单

| 文件 | 阶段 | 动作 |
|---|---|---|
| `impl/core/capability_carrier.py` | 一、二 | 瘦身为协议层；新增 `CapabilityCarrierBase`；bind 改走 provider |
| `impl/core/capability_structured.py` | 一 | 新建，承接结构化形态全部逻辑 |
| `impl/projects/client_search/live.py` | 二 | 增 `capability_provider`；三个物料函数降回项目内部函数，仅被本项目 provider 调用 |
| `impl/core/draft_role_review.py` | 二 | placement 审计改走 `carrier.citation_space()`，删除对 `load_capability_snapshot` 的直接调用 |
| `impl/projects/client_search/capability_lexicon.yaml` 或 manifest | 一 | 承接下沉域词 |
| `impl/core/config_check.py` | 二 | 增"开 scope ⇒ provider 存在"检查 |
| `tests/test_capability_carrier.py` | 一、二 | import 更新；新增装载期检查与 snapshot 等价测试 |
| `spec/alg/capability_carrier.md` | 三 | §3 下沉；新增形态一节 |
| `spec/alg/capability_carrier-reading.md` | 三 | 标注为结构化形态规范 |
| `.claude/skills/evals/SKILL.md` | 三 | 增轴2接入步骤 |
