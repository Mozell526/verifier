# Discovery — judge 泛化（2026-08-15）

Charter: `issues/charter.md`（旧 8 条章程归档为 `issues/charter-split-overstrict.md`）。
尺子：fulfilled.md、material-positioning.md。泛化尺子见章程 §2，不是 341 准确率。
材料：Downloads 两份 xlsx（新 185013 / 旧 205846）、`draft/judge.py` L1479–1525、
`project.yaml` mock scenarios、canvas 方案 E（主张，非 oracle）。
抽取：`issues/trace/name-class-table.json`。

## 已核计数

新表 `/Users/xiaozijian/Downloads/verifier-client_search-cases-20260814-185013.xlsx`：

- N = 341
- `Scenario` 计数：`badcase=341`（0 条非 badcase）
- 新状态：fulfilled=213，not_fulfilled=128
- 精确 2–4 个汉字裸词 `re.fullmatch(r'[\u4e00-\u9fff]{2,4}', user_text)`：n=75，NF=47，F=28
- 其中 live 含 `searchClientName`：n=31，F 只有 3 条（I224 杨杰、I310 郑鑫、I336 匡西永），其余 28 条 NF

旧表 205846 同样 341 条，用于旧状态对照，不改本轮计数。

## 同形态对拍（新 judge 内部）

同一 live 模式 `searchClientName MATCH <token>`，同一个新 judge：

| ID | q | 新 | 咬到的句子 |
|---|---|---|---|
| I224 | 杨杰 | F | 「仅输入杨杰，当作客户本人姓名」 |
| I310 | 郑鑫 | F | 「明确的二字客户姓名」 |
| I336 | 匡西永 | F | 「形态 + 增强规则 + 字段定义佐证」 |
| I485 | 昊轩 | NF | 「字段资料只证明字段语义，未独立证明该词为人名」 |
| I539 | 王坤林 | NF | 「未独立确认其为客户本人姓名」 |
| I168 | 傻生 | NF | 「非百家姓 / 宁可不输出」 |
| I607 | 豆芽 | NF | 「歧义裸词」 |
| I650 | 共展 | NF | 「无独立人名证据」（这条 NF 方向对，机制不得吐回 F） |

邻接、不作 011 主证据：单字「金」I186=F vs 「高」I184=NF / 「任」I535=NF。006 的「配」「周老板」不重开。

## 仓库里没有头部对照集

- 全文搜「正常集 / head set / 对照闸」：只出现在 canvas 方案 E 文案。
- `impl/projects/client_search/project.yaml` 有 mock `default_scenarios`：
  `single_condition, multi_condition_and, product_category_or, product_exclusion,
  age_boundary, premium_unit_conversion, policy_status_filter, unsupported_family_phrase`。
  这是 live 生成场景名，不是冻结的「王坤林 / 姓名+产品 / 合法单号」judge 回归。
- `draft/probes/` 全是 `judge-badcase-*`；`prepare_judge_badcase_cases.py` 也按 badcase 源构造。

## 提示仍是唯一闸

`draft/judge.py` L1479–1525「client_search 直接证据」是姓名 / blocking / 空间的全部条文。
代码侧有 `_unsupported_boundary_evidence` 等工具材料，但没有「2–4 汉字是否姓名」「该维
blocking 与否」「空间表达不了则不得拆 blocking expectation」的确定性过程。
`ClientSearchJudge` 只组 context、调 LLM、normalize。

提示内部打架（已在 006–009 钉过，本轮当源头症状，不重开）：

- L1481 每个可独立判断维度拆一条 expectation
- L1497 字段定义只证明字段语义
- L1504–1508 裸词要独立人名证据，括号里又有「或该形态就是姓名检索」
- L1512–1524 `is_supported=false` 既要「说明不能替代核心」又要「透明说明 blocking=false」；blocking 由模型自选

## 本轮不做什么

- 不重跑 judge，不改 prompt，不改 xlsx / canvas / 产品代码。
- 不把 341 重加权成假头部；不从 341 里挑「看起来正常」当头部集。
- 不重开 006–009。I046/I161 只当 prompt 自选 blocking 的症状。
- 泛化 skill 四条反模式：a 过度规则化；b 只改局部样本；c 只改结果不改源头；d 数据/代码不同步。

## 未消元

- 真实头部流量占比未观测（章程 §4：头部集现造还是等日志 → 用户）。
- 未独立 Load 本轮 catalog 里 `searchClientName` notes 全文；I168 reasoning 引用「百家姓 / 宁可不输出」，peer 应回源。
- 28 条裸词 F 里绝大多数是目录产品/地址/客群标签，不是姓名头部地板。
