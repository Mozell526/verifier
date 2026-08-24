# Check / generalization / elegance / aihacking / business

范围：draft judge 充分性落地。前端 `http://127.0.0.1:8011/index.html` 本轮未起来，未测页面。

| 红线 | 结论 | 证据 |
|---|---|---|
| a 规则化 | 未按题型/role/样本 ID 分流。值=整句是充分性测试，不是覆盖门。打不中 inherit。 | `decide()`；红莲/生存金/李明的重疾险 inherit |
| b 局部改样本 | 未点名王坤林。杨杰与王坤林走同一条 Q1+Q2。 | `name_standard_passes` 读业务源 |
| c 只改结果不改源头 | 删了裸词四句；judge 自己说话。旧 overlay 不再当生产。 | host 文本；`pre_judge` |
| d 数据不一致 | 新实验打新模块。旧 sufficiency dump 只作 field_only 负对照输入。 | `simulate_field_sufficiency_host.py` |
| e 冗余 | 没留裸词兼容层。没新开年龄/产品/保费。 | judge.py 已无 `### 裸词规则` |
| 协议 | 未改 `spec/**`。用已有 `pre_judge` / `reconcile_result`。 | charter §3 |
| 泛化 | 新句子打不中就停。禁止剥虚词。 | 051 |
| 优雅 | 说话时整份替换，避免残留 NF 顶住。标准读业务源 sibling，不抄 341。 | `apply_last_word` |
| aihacking | 无「王坤林例外」。无 fallback 把该失败的放成 F。Q1 失败走 NF。 | 共展/豆芽/金凤当姓名 |
| 业务 | 杨杰/王坤林办成；共展/豆芽失败；红莲保单不因交了姓名就算办成。 | 052 针 |

未做：8011 页面实测；48 次 LLM 重跑；集 B。pre_judge 短路的题不需要 LLM。
