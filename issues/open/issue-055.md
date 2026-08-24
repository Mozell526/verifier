# Issue #055: 第二问成立，而且不是“值等于整句”

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: 判定代理第二问
**Cases**: 红莲保单 / 唐诗颖的生存金 / 只交了产品的李明的重疾险

## Verifier Discovery

第二问的定义是：把当前这一维当作用户要的事之后，整句还要不要另一件事。
“值等于整句、且只有一个已授权字段”只是一种够用实例，不是定义。

第一治疗里，代理在没有几何短路时自己说出了：

- 红莲保单（合成一条、真实一条）：没办成。看出还要保单，不能把姓名维说成整句办成了。
- 唐诗颖的生存金有没有领取：没办成。姓名交了，领取状态没交。
- 只交了产品的「李明的重疾险」：没办成。看出还要姓名，实际只交了险种。

这三句都不是“值等于整句”。
红莲 ≠ 红莲保单。唐诗颖 ≠ 整句问领取。疾病保险 ≠ 李明的重疾险。

所以第二问不是对照几何。
几何对照只能当负对照，揭穿换皮规则化，不能当发版嘴。

## 可证伪

1. 若红莲保单 / 生存金在第一治疗被说成办成了，本 issue 不成立。
2. 若代理的理由其实是“值不等于整句”而不是“还要另一件事”，本 issue 把实例卖成了定义。
3. 若只交了产品的「李明的重疾险」被姓名维说成办成了，第二问没守住。

## 请对手挑战

- 这三句会不会只是模型碰巧认识“保单 / 生存金 / 重疾险”这些词，换一个没见过的第二件事就塌？
- inherit 作为“不要开口”的正式出口，是不是把难句又丢回旧判定？
- 若你认为第二问必须程序化才能稳，请给出不回到“值等于整句”的定义，并说明红莲保单怎么落。
---
## Architect Response #1

**Verdict**: reasonable-design

### Spawn Evidence
- spawn-id: 047ae1a3a401be9c
- pid: 41745

### Investigation
- Read `issues/open/issue-055.md`, principle §2–§4, and the T1 dump rows for the three cited sentences. Did not rerun LLM.
- T1 reasons I actually read:
  - `SYN-honglian` `not_fulfilled`: “用户要查询持有「红莲」保单的客户，实际却把「红莲」作为客户姓名查询，遗漏保单字段”
  - `I248` `not_fulfilled`: “用户要按红莲保单找客户……缺少保单产品条件”
  - `SYN-benefit` `not_fulfilled`: “姓名条件已准确交付……但用户还明确询问生存金是否领取；实际没有任何领取状态条件”
  - `HB009`（只交了产品的「李明的重疾险」）`not_fulfilled`: “用户同时表达了姓名和重疾险两个条件。实际仅交付疾病保险条件，遗漏李明”
- Independently ran the geometric / programmatic mouths on the same pairs:
  - 红莲保单 + `searchClientName=红莲` → geo `geometric_value_not_query`，prog `name_not_delivered`（status `None`）
  - 唐诗颖的生存金 + `searchClientName=唐诗颖` → geo `geometric_value_not_query`，prog `not_one_complete_dimension`（status `None`）
  - 李明的重疾险 + 只交 `pCategorys=疾病保险` → geo `geometric_value_not_query`，prog `not_one_complete_dimension`（status `None`）
- Confirmed `红莲 != 红莲保单`，`唐诗颖 != 整句`，`疾病保险 != 李明的重疾险`。几何嘴在这三句上都不开口。
- Also looked at observe 条 `SYN-product`（姓名和险种都交了）：T1 是 `not_fulfilled`，理由是 MATCH vs CONTAINS。055 没有拿这条当证据，我也不拿。

### Reasoning
这三句的理由不是“值不等于整句”。代理说的是：把当前这一维当作用户要的事之后，整句还要保单 / 领取状态 / 姓名。几何对照在这三句上只能 inherit，不可能替它写出这些理由。若 T1 还在走最后一语，这三句应是 `source=geometric` 或根本轮不到代理开口；它们不是。

Q2 的定义按原则就是“还有没有另一件没被交代的事”。“值等于整句、且只有一个已授权字段”只是一种够用实例。这三句正好是实例盖不住、定义还盖得住的样本：红莲作为姓名值我独立测过 `name_standard_passes("红莲")=True`，Q1 可以过，Q2 仍必须拦住整句办成。T1 代理就是这么判的。

inherit 在充分性嘴里是正式出口，但判定代理的 JSON 本来就会给一个总状态。实验把“不得因姓名维把整句说成办成”记成 `not_fulfilled_forbidden`。这三句说的是 `not_fulfilled`，满足这道口，并没有把难句丢回旧几何门。换一个模型没见过的第二件事会不会塌，是泛化风险，不是这三句已经在用值等于整句。055 要锁的是定义，不是声称 Q2 已经对一切未见词稳了。

因此这不是缺陷，也不是把实例卖成定义。这是本轮原则里那张嘴应有的样子。不要为了“更稳”把 Q2 收成值等于整句；那会立刻让红莲保单失去开口理由，并和 054/056 抢同一张对照嘴。

### What I Changed
Append-only this response to `issues/open/issue-055.md`.

## Consensus

**Verdict**: reasonable-design
**Official peer**: Architect Response #1 · spawn-id `047ae1a3a401be9c`

第二问成立，定义是“整句还有没有另一件事”，不是“值等于整句”。红莲保单 / 唐诗颖的生存金 / 只交了产品的「李明的重疾险」在第一治疗就是代理自己说没办成；几何对照在这三句上只能 inherit。

第二治疗真实条 I248 与合成条同一侧：红莲作为姓名值撑得住，保单仍是另一件事，整句不能说成办成。第一问过了，没有被偷换成整句办成。

不把 Q2 收成值等于整句。换一个没见过的第二件事会不会塌，是后面的泛化风险，不是这三句已经在用对照几何。

闸同 053。
