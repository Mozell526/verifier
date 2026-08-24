# Charter — 第二问必须无歧义，不能再靠「办不了 / 是不是」

> 本轮只辩抽象，不重开 006–028，不改代码，不改协议正文。
> 用户否掉上一轮候选：「今天就办不了吗」本身有歧义和语境偏差；
> 是 / 不是 在该歧义下会导向另一个结果。
> 要求：思考正确抽象，把边界都弄清楚，并且没有任何歧义。

## 1. Goal & Definition of Done

- Goal: 钉死第二问的判定对象、封闭词表、和「办成了没有」的边界；题面换语境不得翻面。
- Done:
  1. 每个根因一个 issue + 协议原文 + 失败对象对照；
  2. architect 独立重读协议后写 Consensus；
  3. 交给用户的是无歧义结构（对象 + 具名状态 + 这不是什么），不是再找一句更顺的口语，也不是上线字段名。

「无歧义」的工作定义（可证伪，不是「任何人第一眼不会读错」）：

1. 换语境不翻面：同一案子，从「看这一次会话」换成「看当前产品」，状态不得变；
2. 失败对象不同格：漏做 ≠ 定位内尚未具备；定位内尚未具备 ≠ 格式外 / 查天气；
3. 不能靠「办成了没有」答完。

## 2. Oracle

- **对错尺子**：`spec/alg/fulfilled.md` 第一章（只看一件事、三态、不区分没办成的原因、不新增第四态）、`spec/alg/authority.md` §1 / §8.2 / §8.3、`spec/alg/material-positioning.md` 不变量 1、`spec/info-volume.md`（不引入 partial、不需要第二套对错）、013–015 / 022–024 Consensus（死路仍死）。
- **不是 oracle**：canvas、准确率、`is_supported=false`、空条件、「暂不支持」文案、常识功能地图、上一轮对外口语「今天就办不了吗」。
- 漏姓名 / 投保年 / 格式外编号 / 查天气 只当碰撞举例，不重判对错，不预填去年 / 称谓。

## 3. Red lines

- Must not touch: `src/**`、产品代码、`impl/projects/client_search/` 生产路径、xlsx、canvas、`draft/judge.py`、协议正文、`issue-006`–`issue-028`。
- May write: `issues/**`、`trace/**`。
- 不发明上线字段，不宣布采用某一句对外中文。

## 4. Escalation

角色不得代选：

1. 要不要对外看见第二问
2. 用哪一句中文当对外题面（结构可锁，终句不可锁）
3. 现在改不改 schema
4. 去年算不算核心 / 称谓认不认 / 格式外算不算单号（仍停住）

## 5. Evidence standards

- 协议原文 + 已锁 Consensus。不得用「我感觉更没有歧义」代替失败对象对照和换语境翻面测试。
- architect 必须自己重读 cited 协议，不抄 verifier 转述。
- 任一候选若换语境会把漏做收进正格，或把格式外 / 查天气收进正格，即未达本轮「无歧义」。

## 6. Budget

- Max argue rounds: 4
- Model for spawned roles: inherit current Codex model
- 不重跑 judge；不改 prompt；不实现字段。

## 7. Cast

- Initiator: verifier
- Opponent: architect
- Reason: 问的是协议分层和题面歧义，不是改 golden，也不是改评测脚手架。
