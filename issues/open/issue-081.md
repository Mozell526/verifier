# Issue #081: 4A 集 B 正式 live KPI —— 真名过严是判定问题，姓名+产品没交姓名是解析问题

**Severity**: high
**Charter**: `issues/charter-judge-agent-t4.md`
**Cases**: HB001–HB018（`impl/projects/client_search/draft/cases/head_set_b.json`，只读）
**Traces**: `issues/trace/name_scenario_runs/HB001.json` … `HB018.json`（2026-08-15 已采，本轮未重跑 live、未改正式文件）
**KPI dump**: `issues/trace/head_set_b_official_live_kpi.json`

## 题面

用户锁了 I007 之后，点名跑 4A：独立头部对照集 B 的完整 live KPI。
集 B 不是从 341 长尾里挑的。18 条，三类：真名 / 真名+产品 / 合法单号，闸上全部期望成功。
没有拆开的 8/18 不得当发版分数。

## 证据（正式 judge，已有 traces）

系统闸（全部期望 fulfilled）：

| 类 | n | 正式 F | 正式 NF |
|---|---|---|---|
| 真名 HB001–008 | 8 | 4 | 4 |
| 真名+产品 HB009–014 | 6 | 0 | 6 |
| 合法单号 HB015–018 | 4 | 4 | 0 |
| 合计 | 18 | 8 | 10 |

拆开以后：

1. **判定过严（live 已交姓名，已有姓名尺也过，正式仍 NF）**
   - HB002 张伟：`searchClientName=张伟`。正式理由：「仅凭裸词……不足以证明其为客户本人姓名」。
   - HB003 王芳：同样已交姓名。正式理由：「裸词……未独立证明王芳为人名」。
   - HB005 周婷婷、HB006 吴志强：同一张额外门槛。
   - 李明 / 陈静 / 马文博 / 欧阳文博 同样是裸词真名，正式却是 F。
   - 这和 1A 直接冲突：2–4 字中文名可单独撑该姓名维。杨杰 / 张伟 / 王坤林必须同侧成功。正式 judge 在集 B 上把张伟打成 NF。

2. **解析没交姓名（正式 NF 是诚实的）**
   - HB009 李明的重疾险：只交了 `pCategorys=疾病保险`
   - HB010 张伟买了年金险：只交了产品
   - HB011 王芳的两全险：只交了险种类别
   - HB012 陈静有没有医疗险：只交了产品
   - HB013 刘洋的增额寿：空条件
   - HB014 赵强买过重疾：只交了险种简称
   - 章程已经写过：真名+产品若 live 没交姓名，诚实保持失败，不算判定胜利。

3. **合法单号**：4/4 正式 F，live 交了客户号或保单号。

## 和 I007 锁的关系

I007「张忠波保单号」只交姓名，用户已锁正式办成。正式 traces 本来就是 F。
集 B 里没有「姓名+无值字段名」这一类。集 B 暴露的是另一件事：正式判定代理在**已经交对了的真名裸词**上，会另设「还要独立证明这是人名」的门槛。这不是 Q2 边界，是 Q1 被模型丢掉、自己加门槛。

红莲保单 / 张伟保单：集 B 没有这两句。I248 没有 live dump。本 issue 不代选。

## 内存对照

T4e 只在内存里跑。原则见 `issues/trace/name-judge-agent-principle.md` §10。
脚本：`issues/trace/simulate_judge_agent_memory_t4e.py`
落盘：`issues/trace/simulate_judge_agent_memory.t4e-extra.json`
不覆盖 `t4.json`，不改 `impl/**`。

T4e 要同时立住：

- I007 只交姓名 → F（项目锁）
- 杨杰 / 王坤林 / 帮忙看看杨杰 → F
- 共展 / 帮忙看看共展 → NF
- 李明的重疾险只交产品 → NF
- 集 B 真名 live 已交姓名 → F（打掉正式那条额外门槛）
- 集 B 姓名+产品 live 没交姓名 → 仍 NF（诚实）
- 红莲保单 / 张伟保单：观察，不锁

## 不是什么

- 不是 341 对错率
- 不是 T4d 13/13
- 不是程序化 8/8
- 不是发版
- 昊轩 / 去年 / 称谓 / 格式外 / 对外中文：仍停住

## T4e 内存成绩（2026-08-16 11:36，不是发版）

只在内存里跑。原则见 `issues/trace/name-judge-agent-principle.md` §10。
脚本：`issues/trace/simulate_judge_agent_memory_t4e.py`
落盘：`issues/trace/simulate_judge_agent_memory.t4e-extra.json`
sha1 `4c7fce733f7bb243a76f2d9df1aef562f1388145`

冻结文件本轮未覆盖：

| 文件 | sha1 |
|---|---|
| `simulate_judge_agent_memory.t4.json` | `4c644304be7a1f2201dc930f0212a354faa93690` |
| `simulate_judge_agent_memory.json` | `a7053bdf749258b8f7c66e3f714d5c7432ef0d07` |
| `head_set_b_official_live_kpi.json` | `33475f8a643cf05b67e64736964284fbfa9813c6` |

启动前 banned 列表为空。原则里没有查一下 / 帮我找 / 保单 / 保单号 / 对象 / 凭证 词表。

### 有政策的针 11 / 0

| id | 问句 | 政策 | T4e |
|---|---|---|---|
| SYN-yangjie | 杨杰 | F | F |
| SYN-gongzhan | 共展 | NF | NF |
| I007 | 张忠波保单号 | F（项目锁） | F |
| SYN-help-look-yangjie | 帮忙看看杨杰 | F | F |
| SYN-please-find-yangjie | 麻烦找下杨杰 | F | F |
| SYN-show-me-wangkunlin | 给我看看王坤林 | F | F |
| SYN-help-look-gongzhan | 帮忙看看共展 | NF | NF |
| SYN-zhangwei-policyno-nameonly | 张伟的保单号 | F | F |
| SYN-query-product-both | 查询李明的重疾险 | F | F |
| HB009-needle | 李明的重疾险（只交产品） | NF | NF |
| SYN-lookup-clientno | 帮我查一下这个客户号 C000888123456 | F | F |

I007 原文理由：

> 第一问：searchClientName值张忠波符合已有字段标准。第二问：原句的具体筛选依据只有张忠波，实际已完整交付；保单号未给具体值，不应虚构条件，也未发现额外限制。

共展仍因第一问姓名尺失败，不是因为说法词。只交产品的「李明的重疾险」仍因第二问缺姓名而 NF。这不是给 I007 开的例外分支。

### 观察针（未锁，不得写成政策）

| id | 问句 | T4e |
|---|---|---|
| I248 | 红莲保单 | F |
| SYN-zhangwei-policy-nameonly | 张伟保单 | F |
| SYN-holdout-zhangwei-policy-info | 张伟保单信息 | F |
| SYN-holdout-please-yangjie | 劳驾查下杨杰 | F |
| SYN-holdout-please-gongzhan | 劳驾查下共展 | NF |

I248 原文理由：

> 第一问：searchClientName值“红莲”符合本轮只读字段标准。第二问：原句可执行的查找依据“红莲”已完整交付，“保单”未给出独立筛选值，实际也未增加无依据限制，因此办成。

同一张 Q2 会把「红莲保单 / 张伟保单」也抬成 F。用户明确说了不要因 I007 代选。本 issue 只记录扩散，不补词表把它们按回去。

### 集 B 17 / 1（不是发版分数）

| id | 问句 | 正式 | T4e | 读 |
|---|---|---|---|---|
| HB001 李明 | F | F | 对齐 |
| HB002 张伟 | NF | **F** | 打掉正式过严 |
| HB003 王芳 | NF | **仍 NF** | 唯一 must_fail |
| HB004 陈静 | F | F | 对齐 |
| HB005 周婷婷 | NF | **F** | 打掉正式过严 |
| HB006 吴志强 | NF | **F** | 打掉正式过严 |
| HB007 马文博 / HB008 欧阳文博 | F | F | 对齐 |
| HB009–014 姓名+产品 | NF | NF | 诚实：解析没交姓名 |
| HB015–018 单号 | F | F | 对齐 |

正式过严 4 条里，T4e 打掉 3 条（张伟 / 周婷婷 / 吴志强），王芳没打掉。

### HB003 王芳：没有为她加规则

T4e 原文：

> 第一问：王芳本身符合姓名字段标准，但MATCH不能保证仅命中完整姓名，已有标准不足以撑住整项交付。第二问：原句唯一筛选依据王芳已交付，AND逻辑正确且无额外条件。

对照：

- 正式理由是另一张门槛：「裸词……未独立证明王芳为人名」。
- T4e 已经承认「王芳本身符合姓名字段标准」，然后另立「MATCH 不能保证只命中完整姓名」。
- 证据源写成了「原始问句」，同批真名成功条用的是 `client_search.condition_compare`。
- 原则已经写了：有已有标准必须消费，不要另立门槛；不要因为问句短就另设门槛。
- 这是模型没把第一问消费完，不是缺一条「王芳算人名」，也不是缺一张 MATCH 词表。

不为王芳加例外。17/1 和 11/0 都不是 ship KPI。

## 审查镜头（本轮只审抽象，不改正式文件）

- 泛化：T4e 改的是第二问测量对象（实际给出的查找依据），不是给「保单号」开分支。王芳翻车若用样本例外去补，就是用户要防的规则化。
- 业务单元格：2–4 字真名、已交姓名、已有姓名尺过 → 该维应办成。王芳满足这个单元格，正式和 T4e 都还没办成，但是两张不同的额外门槛。
- 投机：禁止用「红莲 / 保单」词表把观察针按回 341 旧标；禁止把 I007 写成 if 样本。
- 优雅：还是两问、同一单位。T4d「点到了即使没值也要交」会把已锁的 I007 打成 NF，所以换测量对象，不换出口。

## 请对手挑战

1. 正式张伟 / 王芳 / 周婷婷 / 吴志强 NF，是不是判定过严、和 1A 冲突？若正式嘴有权对裸词另要「独立证明是人名」，拿出项目依据。
2. HB009–014 正式 NF，是不是解析没交姓名、判定这边诚实？若正式判定应直接说办成，说明为什么可以无视没交的姓名。
3. T4e「实际给出的查找依据」是不是抽象，还是藏了一张保单号规则？原则里没有保单 / 保单号词。若离开词表就判不了红莲保单，写清楚——那是观察，不是补词表的许可。
4. T4e 把红莲保单 / 张伟保单抬成 F，是诚实扩散还是越权代选？用户锁的是 I007 这一条边界，不是这两句。
5. 王芳仍 NF。若认为原则有洞，指出洞在哪一问；不要建议「王芳算人名」或 MATCH 词表。
6. 若 T4e 把共展抬成 F、杨杰打成 NF、I007 打成 NF、或把只交产品的「李明的重疾险」抬成 F，才是本轮实问题。本 dump 这四条都没破。
7. 不要把 8/18、11/0、17/1 当发版分数。不要代选昊轩 / 去年 / 称谓 / 格式外 / 对外中文。

082–088 是另一条线（看见层 / 标签），本 issue 不混表。

---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: a4052bc3d0f3de56
- pid: 65784

### Investigation
自己读了 081 全文、集 B 冻结 `impl/projects/client_search/draft/cases/head_set_b.json`（18 条，闸上全部期望 fulfilled）、正式 KPI `issues/trace/head_set_b_official_live_kpi.json`，以及 `name_scenario_runs/HB001–HB015` 和 I007 的 live 条件 / 正式理由。
用 agno python 重读了 KPI 的 `system_gate_expected_all_fulfilled` 和 `judge_vs_parser_split`，与 dump 一致：正式 8 F / 10 NF；`judge_overstrict_live_ok = HB002, HB003, HB005, HB006`；`honest_nf_parser_miss = HB009–HB014`；合法单号 4/4 F。没有重跑 live，没有改正式文件，没有重跑 34 行大模型。

T4e dump sha1 `4c7fce733f7bb243a76f2d9df1aef562f1388145`。集 B 17/1，唯一 must_fail 是 HB003。有政策针 11/0，杨杰 / 共展 / I007 / 只交产品的李明的重疾险都没破。`banned_in_principle=[]`。

独立跑了现有姓名尺 `name_standard_reason`（`simulate_judge_agent_memory.py`，源是 `load_field_standards`，不是样本名单）：

| 值 | 尺 |
|---|---|
| 李明 / 张伟 / 王芳 / 陈静 / 周婷婷 / 吴志强 / 马文博 / 欧阳文博 | 过 |
| 共展 / 豆芽 | 不过（没有该维已识别的姓） |

HB002/003/005/006 的 live 全部是 `searchClientName MATCH <自身>`，和正式 F 的 HB001/004/007/008 同一交付形状。

正式理由原文：

- HB002 张伟 NF：「仅凭裸词和自身姓名字段映射不足以证明其为客户本人姓名」
- HB003 王芳 NF：「用户输入是裸词，现有证据未独立证明王芳为人名」
- HB005 周婷婷 NF：「当前证据仅支持带姓名上下文的规则；周婷婷是裸词」
- HB006 吴志强 NF：「用户输入是裸词……不能独立证明吴志强确为姓名」
- HB001 李明 F：「符合中文姓名结构」
- HB009 李明的重疾险 NF：live 只交 `pCategorys=疾病保险`，「遗漏裸姓名李明」

T4e HB003 原文：「王芳本身符合姓名字段标准，但 MATCH 不能保证仅命中完整姓名，已有标准不足以撑住整项交付。第二问：原句唯一筛选依据王芳已交付」。证据源写成「原始问句」；同批真名成功条用的是 `client_search.condition_compare`。

`issues/decisions.md` 1A 的例子就是「李明」「周婷婷」。049 已删 draft judge 的裸词四句；当前 `impl/projects/client_search/draft/judge.py` 里搜不到「裸词规则 / 独立姓名证据」。

### Reasoning
拆开以后，081 的主结论成立。8/18 不是发版分数。

**1. 四个真名正式 NF 是判定过严，和 1A 冲突。**
1A 写的是：用户只输入「李明」「周婷婷」这种 2–4 字中文名，系统已经按客户姓名去搜，算办成。周婷婷就是 1A 的例子，正式却打 NF。张伟 / 王芳 / 吴志强与李明 / 陈静 / 马文博同一单元格：2–4 字、有姓、已交 `searchClientName`、现有姓名尺过。正式一边用「中文姓名结构」放行李明，一边要「独立证明是人名」打死张伟，不是另一套项目授权，是同一张嘴丢掉 Q1、自己加门槛。

正式嘴有没有权对裸词另要独立证明？没有。那条「裸词要独立人名证据」在 049 已经从正式提示删掉。本轮正式理由把删掉的门槛又说回来了。fulfilled.md §2.1 的「要有证据」不能拿来覆盖 1A：对这个单元格，证据就是现有姓名尺 + 这次交了这个姓名。共展 / 豆芽过不了尺，所以仍应 NF；不能把那条负例倒灌成「凡裸词都要第二份人名证明」。

**2. HB009–014 正式 NF 是解析没交姓名，判定这边诚实。**
六条 live 都没有 `searchClientName`（HB013 空条件）。问句里「李明 / 张伟 / 王芳 / 陈静 / 刘洋 / 赵强」是已经给出的查找值。正式说缺姓名，没有把问句收到产品维，也没有因为闸上期望 fulfilled 就改口办成。T4e 同样 NF。这不是判定胜利，也不是判定该说 F。

**3. T4e「实际给出的查找依据」是抽象，不是藏词表。**
原则正文没有保单 / 保单号。I007 与只交产品的「李明的重疾险」对错相反，靠的是「有没有给出可查找的值」。红莲保单离开「剩余名词算不算字段名」仍判不稳——这是观察，不是补词表的许可。

**4. 红莲 / 张伟保单抬成 F，是诚实扩散，不是代选。**
用户锁的是 I007 这一条边界。T4e 把这两句放在 observe，政策是 `null`。同一张 Q2 会倾向 F，必须记扩散，不得写成已锁。不得补「保单 / 保单号」把它们按回 341 旧标。

**5. 王芳仍 NF，洞不在缺「王芳算人名」，也不在 MATCH 词表。**
T4e 已经承认「王芳本身符合姓名字段标准」，第二问也说依据已交付，然后另立「MATCH 不能保证只命中完整姓名」。原则 Q1 已经写了：必须消费已有标准，不要另立门槛；不要因为问句短就另设门槛。同批张伟 / 周婷婷 / 吴志强 / 李明 也是 MATCH，只有王芳被这根新尺打死。这是模型没把第一问消费完。洞在 Q1 的「消费完就停」，不在姓名尺缺王芳，也不在要不要给 MATCH 加词表。

**6. 本 dump 没破发起人列的四条实问题。**
共展仍 NF，杨杰仍 F，I007 仍 F，只交产品的「李明的重疾险」仍 NF。11/0 与 17/1 都不是 ship。昊轩 / 去年 / 称谓 / 格式外 / 对外中文不代选。082–088 不混表。

所以 081 不是「集 B 没过、整张嘴重写」。真问题只有正式判定在 1A 真名单元格上重建裸词门槛。解析漏姓名保持诚实 NF。T4e 是内存对照，打掉 3/4 过严条、留下王芳，恰好说明不要用样本例外去补。

### Improvement Proposal
- **Target**: 正式判定代理在集 B 真名单元格上的 Q1 消费。权威口径是 `issues/decisions.md` 1A 与已有 `name_standard_reason`，不是 `head_set_b.json` 名单，也不是 T4e 17/1。本轮章程禁止改 `impl/**` / `spec/**` / `draft/judge.py`；本 peer 只读，只写提案。
- **Change**:
  1. 4A 正式读法锁成 KPI 里已经拆开的三行，不得再报 8/18：
     - 真名：live 已交 `searchClientName` 且现有姓名尺过 → 该维必须 F。HB002 / HB003 / HB005 / HB006 是判定过严。
     - 真名+产品：live 没交姓名 → 正式 NF 诚实，算解析，不算判定。
     - 合法单号：4/4 F，保持。
  2. 正式嘴禁止在这个单元格重建「裸词还要独立证明是人名」。049 已删的四句不得以任何措辞回到提示。不得加「张伟 / 王芳 / 周婷婷 / 吴志强算人名」。
  3. Q1 操作定义（不要第三问）：对该字段已有标准，过了就停。`searchClientName=王芳` 且尺过，不得再审 MATCH 会不会命中同姓其它人。那不是已有标准。
  4. 红莲保单 / 张伟保单继续观察。I007 锁不得自动扩过去。禁止保单 / 保单号词表。
  5. T4e 只留在内存。17/1、11/0、8/18 都不是发版分数。
- **Verification**:
  ```bash
  /Users/xiaozijian/miniconda3/envs/agno/bin/python -c "import json; from pathlib import Path; d=json.loads(Path('issues/trace/head_set_b_official_live_kpi.json').read_text()); print(d['system_gate_expected_all_fulfilled']); print(d['judge_vs_parser_split'])"
  ```
  正式判定以后若重跑这 8 条真名（本轮不要跑）：HB001–HB008 在 live 仍只交对应姓名时，必须全部 F。HB009–HB014 在 live 仍缺姓名时，必须仍 NF。禁止出现「王芳例外」或 MATCH 词表。内存侧只准读已有 `simulate_judge_agent_memory.t4e-extra.json`，不准把 17/1 写进发版材料。

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `a4052bc3d0f3de56`

闸同 076 r2。没有重跑 34 行，没有重采 live。独立核过正式 KPI 拆开三行：过严 HB002 / HB003 / HB005 / HB006；解析没交姓名 HB009–014；单号 4/4 F。T4e 集 B 17/1，唯一 must_fail 是 HB003。王芳原文仍是「符合姓名字段标准，但 MATCH 不能保证仅命中完整姓名」。

接受 #1。

正式过严成立。张伟 / 王芳 / 周婷婷 / 吴志强 live 已交姓名、现有姓名尺过，周婷婷就是 1A 的例子。正式嘴在这个单元格上重建了 049 已删的「裸词还要独立证明是人名」。这和 1A 冲突，不是另一套项目授权。

HB009–014 正式 NF 是解析没交姓名，判定这边诚实。不是判定胜利，也不是判定该说办成。

4A 正式读法锁成已经拆开的三行。没有拆开的 8/18 不得当发版分数。11/0、17/1 也不是发版分数。

王芳不加点名例外，不加 MATCH 词表。洞在第一问「已有标准过了就停」，模型自己又立了一根检索完整性尺。同批张伟 / 周婷婷 / 吴志强也是 MATCH，只有她被这根新尺打死。

红莲保单 / 张伟保单继续观察。I007 锁不得自动扩过去。禁止保单 / 保单号词表。

#1 提案只读。本轮不改 `impl/**` / `spec/**` / `draft/judge.py`。T4e 只留在内存。昊轩 / 去年 / 称谓 / 格式外 / 对外中文不代选。082–088 不混表。
