# Issue #009: 「明确对象 + 空条件 = NF」盖住格式外/称谓的合法拒识

**Class**: boundary
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output + code-analysis
**Layer**: Configuration
**Cases**: I034 大写P07。六个零。（过严）；I616 与 #006 交叉，本 issue 只取「空条件必须交出去」这条机制

## Verifier Discovery

### I034

query：`大写P07。六个零。` 可展开为 `P07000000`（P + 8 位）。

同 live：`conditions=null`，robot「未识别到明确查询条件」。旧 F / 新 NF。

新：唯一 blocking「按保单号检索P07后六个零的客户」，expected 强制 `polNo MATCH P07000000`。reasoning：用户明确给出可展开编号，空条件就是没交付。

旧：`P07000000` 长度不像合法保单号，正确行为是不生成条件。历史字段口径（`draft/retry-reports/001-provider-retry.json`）：`standard_format` = 「P或A开头后跟15至17位数字或字母，兼容历史14位；未知位不得补0、重复或猜测」。`P07000000` 短于该空间。positioning §4：空间外值是发现信号，不是该交出去的条件。

### 机制

`draft/judge.py` L1513–1519 两句同时在场：

1. 「以下内容永远不能单独成为 blocking 核心交付：…拒绝越界请求、告知当前限制、未识别到条件」
2. 「若请求存在明确业务对象但 actual 没有可执行条件…按当前交付判 not_fulfilled」

第 2 句把口述编号当成必须交付的对象。第 1 句又禁止把「拒绝越界」当核心。模型咬住第 2 句：没 MATCH 出去就 NF。本轮 I034 的 evidence 只 Load 了 polNo 支持 MATCH，没核格式空间。

I616 同一闸：把「周老板」当成明确业务对象，空条件 → NF。称谓不是可执行姓名（见 #006）。

### 协议

- §4.1 查不了：职责内本可支持却没给 → NF。格式外编号不是「本可支持」。
- §4.5 该回结果没回：职责内没有任何可用输出 → NF。前提是职责内且该交。
- §3.1 空条件不得因此逃到 NE（Authority 关）。「不得 NE」≠「必须 NF」。合法拒识可以是 F（守空间）或至少不因「没交非法值」打 NF。

### 未消元

- 本轮新 judge JSON 未附 polNo 格式 Load；格式句来自历史 retry-report 与旧 judge，peer 应回源字段定义。
- 「老板」是否在某些业务里可当检索别名，未查。

---
## architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 5f7ddad9f3a27ddc
- pid: unknown

### Investigation
- 复核 trace I034：live `conditions=null` + robot「未识别到明确查询条件」，old=F / new=NF。新 judge `expected` 强制 `polNo MATCH P07000000`，reasoning「用户明确给出可展开编号…未交付保单号MATCH条件」。
- 证据不对称逐字坐实：新 judge `evidence` 只有 `loaded_field_definition{polNo, operators=[MATCH]}`（无格式/长度）；旧 judge `evidence` 含 `capability_manifest.polNo`「保单号要求P或A开头后跟15至17位字符，兼容历史14位；P07000000不满足该格式」。新 judge 确实没核格式空间就要 MATCH。
- 位数核算：`P07000000` 总长 9、去前缀 8；格式要求前缀+15–17（历史14）即总长 16–18（历史15）。9 远低于下限，属空间外，结论对「历史14位」按总长或按后缀两种读法都稳健。
- 回源 verifier「未消元#1」：`draft/retry-reports/001-provider-retry.json` 原文 `standard_format: "P或A开头后跟15至17位数字或字母，兼容历史14位；未知位不得补0、重复或猜测"`，与旧 judge 口径一致（真正权威源是外部 `field_definitions_args.yaml`，repo 内不可读，但 9 位远低于任何下限，不影响结论）。
- 核对 `draft/judge.py` L1513「…拒绝越界请求、告知当前限制、未识别到条件 永远不能单独成为 blocking 核心交付」与 L1514–1519「明确业务对象但 actual 无可执行条件…判 not_fulfilled」同段并存。
- 复核协议：fulfilled §4.1「职责内（本可/本应支持却没给）→ 没办成」、§4.5 前提「职责内且该交」、§3.1「空 conditions 不得触发 not_evaluable」；positioning §4 不变量3「空间外输出是发现信号，不是空间的一部分」、§8.3「不得把漂移解释成空间的一部分」。

### Reasoning
新 judge 的 NF 站不住，机制与证据两层都输：

1. 机制：L1514–1519「明确业务对象 + 空条件 → NF」没有「该对象是否空间内可交付」的前置判断，把口述编号直接当必须交付对象；同段 L1513 又写「拒绝越界请求不能当 blocking 核心」。模型咬住前句，对格式外编号也强判 NF。
2. 证据：要判「本可支持却没给」（§4.1），得先证明「本可支持」。新 judge 只 Load 了 polNo 支持 MATCH，没 Load 格式空间，等于没核「P07000000 是否可交付」就下 NF——证据链缺了关键一环。P07000000 实际在格式空间外，positioning 明确空间外值是发现信号、不该被交出去；强要 MATCH 它反而是在要求一次空间外输出。

所以「没交非法值」不构成 NF。verifier 的最低主张「至少不因『没交出去』打 NF」成立。I616 同闸（把称谓当必须交付姓名）机制相同。

一处必须补强的修正（verifier 的「可以是 F」需谨慎）：fulfilled §7.1 / §5 / D3 反复明确「系统如实拒绝用户查不了的东西 → 整体算办成了 ✗」「如实拒绝、态度好 ≠ 办成」。旧 judge 在 I034 正是把「正确拒绝生成非法保单号」写成 blocking 并判 fulfilled——这本身就是 D3 要删的「如实拒绝=办成」口径。因此本 issue 的正确结论不是「旧 F 对、新 NF 错」，而是「新 NF 错（强要空间外交付）」；但修回去的目标**不应**是恢复旧的「拒绝=F」，否则会把新 judge 本来修掉的 D3 漏洞又请回来。更贴协议的落点：格式外/称谓这类不可执行对象，空条件+未识别不应打 NF，可落「输入坏/依据不充分」的 not_evaluable（§3.1 允许 Authority 关闭时因输入坏判 NE，触发因是『输入不可用』而非『空条件本身』，不违反『空条件不得逃 NE』），或按非 blocking 说明处理——由用户在章程 §4 裁定，但方向上排除「拒绝=F」与「强 NF」两端。

不是 reasonable-design：新 judge 未核格式即强判 NF，是证据缺失下的过严，不是约束下的取舍。

### Improvement Proposal
（permission mode = review，章程红线禁改 judge；建议交由有写权限角色在用户裁定后实施）
- **Target**: `impl/projects/client_search/draft/judge.py` L1513–1519（「明确业务对象 + 空条件 → NF」规则加前置闸）。
- **Change**: 给该规则加可交付性前置：仅当对象在当前空间可表达（格式/枚举/字段匹配已 Load 确认）时才因空条件判 NF；对象为格式外编号、称谓、空间外值时，空条件+未识别不得判 NF。落点二选一由用户定：(a) not_evaluable（输入坏/依据不充分，附缺料清单），或 (b) 非 blocking 说明。**明确禁止**回退到「拒绝越界=blocking F」（fulfilled §7.1/D3）。同时要求判「本可支持」前必须已 Load 格式/值空间，杜绝「只看 operator 不看格式」的证据缺口。
- **Verification**: 同 live 重跑 I034、I616（期望不再 NF，也不得出现「拒绝=F」）；对照「合法保单号却空条件」的真漏识别 case 仍须 NF，确认闸门不误放职责内漏交付。

---
## Consensus
**Verdict**: real-problem
**Summary**: I034 新 NF 错——没核格式空间就要 MATCH 出 `P07000000`（9 位，格式下限 15–18）。接受 peer 修正：正确落点**不是**恢复旧 F。旧 F 正是 D3/§7.1 禁止的「如实拒绝=办成」。格式外/称谓：空条件不得 NF，也不得 F；落 NE（输入坏）还是 non-blocking 说明，用户定。合法保单号空条件仍须 NF。

