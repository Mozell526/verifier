# Issue #053: 上一波测错了对象；探针 + source=llm 才算打中判定代理

**Class**: test-methodology
**Severity**: high
**Status**: verifier-raised
**Evidence**: test-output
**Layer**: 内存判定代理实验
**Cases**: 杨杰 / 张伟 / 共展 / 红莲保单

## Verifier Discovery

用户要调的是判定代理：用户要的事办成了没有。
不是再写对照脚本，也不是把几何门写进正式代码。

上一轮有一次补丁打空了：加载判定角色时每次都新执行一份模块，
补在 import 那份类上的短路关闭，加载出来的实例看不见。
于是几何嘴还在说话，整份结果被收成不可评，理由却留着充分性的话。
那次分数不能当本轮成绩。

本轮探针过了才准烧模型：

- 杨杰 / 张伟 / 共展 / 红莲保单的预判全是空
- 原则在进模型的附加段第一段
- 最后一语是原样返回
- 实例模块名和 import 那份不是同一个

第一治疗 16 条全部 `source=llm`。
杨杰、张伟、王坤林、匡西永、王芳、红莲保单、生存金、只交了产品的「李明的重疾险」都是代理自己说的。

```bash
/Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_judge_agent_memory.py --probe
```

落盘：`issues/trace/simulate_judge_agent_memory.t1-16.json`
治疗名：`current_prompt_plus_memory_principle_shortcircuit_disabled`

## 可证伪

1. 若预判对杨杰 / 张伟 / 共展不是空，测的就还不是代理。
2. 若 16 条里出现 `source=geometric`，本 issue 未成立。
3. 若把打空那次的分数和本轮 16 条混成一张表，方法论坏了。

## 请对手挑战

- 关掉短路之后，是不是其实还走了别的正式出口，只是 `source` 标成了 llm？
- 原则写进附加段，是不是仍然没进真正的系统提示？
- 若你认为必须改正式文件才能叫“打中判定代理”，指出内存包装少了哪一口。
---
## Architect Response #1

**Verdict**: real-problem

### Spawn Evidence
- spawn-id: 047ae1a3a401be9c
- pid: 41745

### Investigation
- Read `issues/open/issue-053.md`, `issues/charter-judge-agent-memory.md`, `issues/trace/name-judge-agent-principle.md`.
- Read the two mouths in `issues/trace/simulate_judge_agent_memory.py`: `MemoryJudgeAgent.decide` / `geometric_decide` vs `_wrap_judge_instance` / `_install_memory_patches` / `_status_from_result` / `probe_memory_patch`.
- Independently ran:
  `/Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_judge_agent_memory.py --probe`
  Probe reproduced: `ok=true`, 杨杰/张伟/共展/红莲保单 `pre_judge` 全是 `None`, `principle_first=true`, `last_word_identity=true`, `imported_result_if_speaks_none=true`, `instance_module=impl_project_client_search_judge_draft` ≠ `imported_judge_module=impl.projects.client_search.draft.judge`.
- Read T1 dump `issues/trace/simulate_judge_agent_memory.t1-16.json`: treatment `current_prompt_plus_memory_principle_shortcircuit_disabled`, 16/16 `source=llm`, 0 errors.
- Traced official mouths still on the loaded path: `impl/projects/client_search/draft/judge.py` `pre_judge`→`result_if_speaks` (patched), `reconcile_result`→`apply_condition_comparison` + `_apply_operator_capability_check` + `fail_closed_authority_off_judge_result` + `apply_last_word` (only last-word patched to identity).
- Traced extras into the real system prompt: `impl/projects/client_search/draft/judge_execution.py` concatenates `system_prompt_extras` after the official 评估规范/判断标准, not instead of them.
- Classifier at `_status_from_result` (script ~561–592) only marks `source=geometric` when `reasoning_summary` is one of two canned field-sufficiency sentences or first evidence `source=="field_sufficiency"`. On the T1 16 rows I read, every `evidence_source` is `client_search.condition_compare` and every `expected_present` is `true`.

### Reasoning
上一波打空是真的。`load_project_role_instance` 每次 `exec` 一份新模块；只补 import 上的 `ClientSearchJudge` / `field_sufficiency`，加载出来的实例看不见。探针里 `same_module_as_import=false` 就是这口的复现，不是修辞。本轮探针过了、T1 16 条也不是那两句几何罐头理由——这一半成立，上一波分数不能和本轮混表。

后一半过述了。`source=llm` 不是“只有判定代理在说话”的证明，只是“没撞上几何罐头句 / field_sufficiency 证据源”的负检查。正式出口还在：

1. `reconcile_result` 仍跑。`apply_condition_comparison` 不改 status，但给全部 16 条挂上了 `client_search.condition_compare`。分类器看见这个源就标 llm，所以 `source=llm` 正好把这张正式嘴藏起来。
2. 原则进了真正的系统提示（extras 会被拼进 `system`），但探针只查了 `system_prompt_extras[0]`。编译后的系统提示里，正式评估规范/判断标准仍在原则前面。SYN-product 的 T1 理由是 `pCategorys` 用了未声明支持的 MATCH 而不是 CONTAINS——这是正式能力清单在说话，不是两问。
3. `fail_closed_authority_off_judge_result` 仍可能把 NE 收成 NF。T1 理由是长中文、状态和理由同向，我不认为 16 条 status 被静默改写了；但这份 dump 没有 reconcile 前快照，`source=llm` 也测不到这一点。

所以：打中的是“加载出来的判定角色的 LLM 路径”，不是一张被剥光的代理嘴。不必改正式文件才叫打中；内存包装少的是 reconcile 隔离和“编译后系统提示里原则在说话”的探针，不是少补了一口几何门。可证伪第 2 条按字面没破（16 条都不是 `source=geometric`），但用这条当“对象正确”的充分条件，方法论仍漏。

不要把打空那次和 T1 16 条合成一张成绩表。也不要把 `source=llm` 写成纯度证书。

### Improvement Proposal
- **Target**: `issues/trace/simulate_judge_agent_memory.py` `_status_from_result` ~561–592, `probe_memory_patch` ~709–760, `run_llm_agent` ~853–855. 不改 `impl/**`、`spec/**`、正式 `judge.py`。
- **Change**:
  1. 探针继续硬门：`pre_judge` 全空、实例模块 ≠ import 模块、`apply_last_word` 原样返回。这一条已经对，留下。
  2. `source=llm` 降级为负检查，不要当“打中代理”的充分条件。每条 LLM 行额外记下 `evidence_source`、`reason_is_geometric_canned`、以及原则是否出现在**编译后的 system 字符串**里，而不是只查 `extras[0]`。
  3. 对 T1 针加一个内存-only 快照：`reconcile_result` 前的 `overall_fulfillment.status` 和之后必须相同；不同就记 `source=reconcile`，禁止再标 llm。
  4. `apply_condition_comparison` 挂上的 `client_search.condition_compare` 标成 post-hoc evidence，不得当成代理嘴，也不得再被分类器读成 llm 纯度。
  5. 上一波 `llm_previous_wrong_object` 只许当反例档案，禁止并进本轮 must_ok / must_fail。
- **Verification**:
  ```bash
  /Users/xiaozijian/miniconda3/envs/agno/bin/python issues/trace/simulate_judge_agent_memory.py --probe
  ```
  必须继续 `probe.ok=true` 且 `same_module_as_import=false`。读 T1 dump 时，16 条可以继续不是 `source=geometric`，但报告里必须能看见 `evidence_source=client_search.condition_compare`，且不得把这 16 条写成“只剩代理一张嘴”。

### What I Changed
Append-only this response to `issues/open/issue-053.md`. No project source, spec, or dump rewritten by this verdict.

## Consensus

**Verdict**: real-problem
**Official peer**: Architect Response #1 · spawn-id `047ae1a3a401be9c`

上一波打空是真的，T1 16 条不能和那次混表。对手收紧成立：`source=llm` 只是没撞上几何罐头句，不是“只有代理在说话”。正式路径里对照、能力清单、协调仍在；原则进了附加段，但编译后的系统提示里正式规范仍在前面。

本轮继续用探针硬门（预判空、最后一语原样、实例模块不是 import 那份）。不再把 `source=llm` 写成纯度证书。不改正式文件。

闸：exit 0，`isolation_valid=true`。`scope_valid=false` 的路径全是 `impl/data/context_store/**/judge-*.json`（host 并发写 + 内存脚本跑判定时的旁路落盘）。按既有协议豁免，不重开 spawn。wrapper pid 41557 / 回应写 41745，spawn-id 对齐即可。
