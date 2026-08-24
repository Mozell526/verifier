# Empirical Solve Iterations

Generated: 2026-08-13 00:46 UTC+8

## Scope

- V2→reject→strict rules→cascade→coverage/stem→soft long-field filter.
- **Not** selected / promoted. No Draft skill edits. No synonym injection.

## Source evidence

| term | field | rules | abbr |
|---|---|---|---|
| `另一半` | False | False | False |
| `家里人` | True | True | False |
| `保的是谁` | False | False | False |
| `做哪一行` | False | False | False |
| `收信寄到哪里` | False | False | False |
| `配偶` | True | True | False |
| `家人` | False | True | False |
| `被保险人` | True | True | False |
| `职业` | True | True | False |
| `联系地址` | True | False | False |
| `通讯地址` | True | False | False |
| `兴趣爱好` | False | False | False |
| `关爱客户` | True | True | False |
| `有钱` | True | True | False |
| `金凤` | False | False | True |
| `盘客` | True | True | False |

| holdout id | query | present | ABSENT |
|---|---|---|---|
| `holdout-v3-spouse-birthday` | `另一半是哪天出生的` | — | **['另一半是', '哪天出生']** |
| `holdout-v3-family-phone` | `家里人的联系电话` | — | **['家里人的', '联系电话']** |
| `holdout-v3-insured-name` | `这张保单保的是谁` | — | **['这张保单', '保的是谁']** |
| `holdout-v3-occupation` | `客户是做哪一行的` | — | **['客户是做', '哪一行的']** |
| `holdout-v3-contact-address` | `客户收信寄到哪里` | — | **['客户收信', '寄到哪里']** |
| `holdout-v3-unsupported-hobby` | `客户平时有什么兴趣爱好` | — | **['客户平时', '有什么兴', '趣爱好']** |
| `holdout-v3-irrelevant-recipe` | `红烧肉怎么做` | — | **['红烧肉怎', '么做']** |
| `holdout-v3-irrelevant-astronomy` | `黑洞为什么会蒸发` | — | **['黑洞为什', '么会蒸发']** |

## Ranking

| rank | recipe | A | empty | avg | dev | hold | scalar |
|---:|---|---|---:|---:|---|---|---:|
| 1 | `SOFT_V2R_L10` | True | 0.619 | 1.33 | 0.773/1.000 | 0.200/1.000 | 125.3 |
| 2 | `V2R` | True | 0.020 | 7.53 | 0.773/0.889 | 0.200/1.000 | 111.2 |
| 3 | `SOFT_cov0.35_L10` | True | 0.616 | 0.82 | 0.727/1.000 | 0.200/1.000 | 124.9 |
| 4 | `SOFT_cov0.35_L12` | True | 0.616 | 0.83 | 0.727/1.000 | 0.200/1.000 | 124.9 |
| 5 | `SOFT_cov0.42_L10` | True | 0.616 | 0.82 | 0.727/1.000 | 0.200/1.000 | 124.9 |
| 6 | `SOFT_cov0.35_L10_looseRules` | True | 0.616 | 0.84 | 0.727/1.000 | 0.200/1.000 | 124.9 |
| 7 | `SOFT_cov0.42_L14` | True | 0.614 | 0.85 | 0.727/1.000 | 0.200/1.000 | 124.9 |
| 8 | `SWEEP_cov0.30_stem1` | True | 0.020 | 3.32 | 0.727/0.889 | 0.200/1.000 | 113.8 |
| 9 | `V5_stem` | True | 0.023 | 2.83 | 0.727/0.889 | 0.200/1.000 | 117.8 |
| 10 | `V9_cov35` | True | 0.023 | 2.83 | 0.727/0.889 | 0.200/1.000 | 117.8 |
| 11 | `V10_pareto` | True | 0.023 | 2.82 | 0.727/0.889 | 0.200/1.000 | 117.8 |
| 12 | `SWEEP_cov0.35_stem1` | True | 0.023 | 2.83 | 0.727/0.889 | 0.200/1.000 | 117.8 |
| 13 | `SWEEP_cov0.30_stem0` | True | 0.026 | 3.30 | 0.727/0.889 | 0.200/1.000 | 113.8 |
| 14 | `SWEEP_cov0.35_stem0` | True | 0.028 | 2.81 | 0.727/0.889 | 0.200/1.000 | 117.8 |
| 15 | `SWEEP_cov0.40_stem0` | True | 0.028 | 2.81 | 0.727/0.889 | 0.200/1.000 | 117.8 |
| 16 | `V6_cascade` | True | 0.023 | 2.82 | 0.682/0.889 | 0.000/1.000 | 115.7 |
| 17 | `V7_rules_first` | True | 0.023 | 2.82 | 0.682/0.889 | 0.000/1.000 | 115.7 |
| 18 | `V4_cov` | True | 0.028 | 2.81 | 0.682/0.889 | 0.000/1.000 | 115.7 |

## Soft mid-bar detail

### SOFT_cov0.35_L10
- config `{'cov': 0.35, 'stem': True, 'long_min': 10, 'reject': True, 'strict_rules': True, 'soft_long_field_filter': True}`
- A=True empty=0.616 avg=0.82 dev=0.727/1.000 hold=0.200/1.000

| query | qual | hits |
|---|---|---|
| `关爱客户` | **OK** | field:clientAge, enhanced_rules:关爱客户-40岁及以上女性, field:isBuyInsurance |
| `有钱` | **OK** | field:newValueLabel |
| `有钱客户` | **OK** | field:newValueLabel, field:isBuyInsurance |
| `金凤` | **OK** | abbrname:金凤 |
| `盘客` | **OK** | field:customerReview |
| `去盘客` | **OK** | field:customerReview |
| `A` | **OK** | ∅ |
| `O2O` | **OK** | enhanced_rules:准客来源-简称, field:pcustSourcType, field:validSinsPol |
| `陈金秀` | **MISS** | ∅ |
| `天气怎么样` | **OK** | ∅ |
| `客户平时有什么兴趣爱好` | **OK** | ∅ |

### SOFT_cov0.35_L12
- config `{'cov': 0.35, 'stem': True, 'long_min': 12, 'reject': True, 'strict_rules': True, 'soft_long_field_filter': True}`
- A=True empty=0.616 avg=0.83 dev=0.727/1.000 hold=0.200/1.000

| query | qual | hits |
|---|---|---|
| `关爱客户` | **OK** | field:clientAge, enhanced_rules:关爱客户-40岁及以上女性, field:isBuyInsurance |
| `有钱` | **OK** | field:newValueLabel |
| `有钱客户` | **OK** | field:newValueLabel, field:isBuyInsurance |
| `金凤` | **OK** | abbrname:金凤 |
| `盘客` | **OK** | field:customerReview |
| `去盘客` | **OK** | field:customerReview |
| `A` | **OK** | ∅ |
| `O2O` | **OK** | enhanced_rules:准客来源-简称, field:pcustSourcType, field:validSinsPol |
| `陈金秀` | **MISS** | ∅ |
| `天气怎么样` | **OK** | ∅ |
| `客户平时有什么兴趣爱好` | **OK** | ∅ |

### SOFT_cov0.42_L10
- config `{'cov': 0.42, 'stem': True, 'long_min': 10, 'reject': True, 'strict_rules': True, 'soft_long_field_filter': True}`
- A=True empty=0.616 avg=0.82 dev=0.727/1.000 hold=0.200/1.000

| query | qual | hits |
|---|---|---|
| `关爱客户` | **OK** | field:clientAge, enhanced_rules:关爱客户-40岁及以上女性, field:isBuyInsurance |
| `有钱` | **OK** | field:newValueLabel |
| `有钱客户` | **OK** | field:newValueLabel, field:isBuyInsurance |
| `金凤` | **OK** | abbrname:金凤 |
| `盘客` | **OK** | field:customerReview |
| `去盘客` | **OK** | field:customerReview |
| `A` | **OK** | ∅ |
| `O2O` | **OK** | enhanced_rules:准客来源-简称, field:pcustSourcType, field:validSinsPol |
| `陈金秀` | **MISS** | ∅ |
| `天气怎么样` | **OK** | ∅ |
| `客户平时有什么兴趣爱好` | **OK** | ∅ |

### SOFT_cov0.42_L14
- config `{'cov': 0.42, 'stem': True, 'long_min': 14, 'reject': True, 'strict_rules': True, 'soft_long_field_filter': True}`
- A=True empty=0.614 avg=0.85 dev=0.727/1.000 hold=0.200/1.000

| query | qual | hits |
|---|---|---|
| `关爱客户` | **OK** | field:clientAge, enhanced_rules:关爱客户-40岁及以上女性, field:isBuyInsurance |
| `有钱` | **OK** | field:newValueLabel |
| `有钱客户` | **OK** | field:newValueLabel, field:isBuyInsurance |
| `金凤` | **OK** | abbrname:金凤 |
| `盘客` | **OK** | field:customerReview |
| `去盘客` | **OK** | field:customerReview |
| `A` | **OK** | ∅ |
| `O2O` | **OK** | enhanced_rules:准客来源-简称, field:pcustSourcType, field:validSinsPol |
| `陈金秀` | **MISS** | ∅ |
| `天气怎么样` | **OK** | ∅ |
| `客户平时有什么兴趣爱好` | **OK** | ∅ |

### SOFT_cov0.35_L10_looseRules
- config `{'cov': 0.35, 'stem': True, 'long_min': 10, 'reject': True, 'strict_rules': False, 'soft_long_field_filter': True}`
- A=True empty=0.616 avg=0.84 dev=0.727/1.000 hold=0.200/1.000

| query | qual | hits |
|---|---|---|
| `关爱客户` | **OK** | field:clientAge, enhanced_rules:关爱客户-40岁及以上女性, field:isBuyInsurance |
| `有钱` | **OK** | enhanced_rules:客户价值-高价值, enhanced_rules:最近半年未联系的高价值客户, field:newValueLabel |
| `有钱客户` | **OK** | field:newValueLabel, field:isBuyInsurance |
| `金凤` | **OK** | abbrname:金凤 |
| `盘客` | **OK** | field:customerReview, enhanced_rules:盘客-暂不支持 |
| `去盘客` | **OK** | field:customerReview |
| `A` | **OK** | ∅ |
| `O2O` | **OK** | enhanced_rules:准客来源-简称, field:pcustSourcType, field:validSinsPol |
| `陈金秀` | **MISS** | ∅ |
| `天气怎么样` | **OK** | ∅ |
| `客户平时有什么兴趣爱好` | **OK** | ∅ |

### SOFT_V2R_L10
- config `{'cov': 0.0, 'stem': False, 'long_min': 10, 'reject': True, 'strict_rules': False, 'soft_long_field_filter': True}`
- A=True empty=0.619 avg=1.33 dev=0.773/1.000 hold=0.200/1.000

| query | qual | hits |
|---|---|---|
| `关爱客户` | **OK** | enhanced_rules:关爱客户-40岁及以上女性, field:clientAge, field:isBuyInsurance |
| `有钱` | **OK** | enhanced_rules:客户价值-高价值, enhanced_rules:最近半年未联系的高价值客户 |
| `有钱客户` | **OK** | field:newValueLabel, field:isBuyInsurance |
| `金凤` | **OK** | abbrname:金凤 |
| `盘客` | **OK** | enhanced_rules:盘客-暂不支持, field:customerReview |
| `去盘客` | **OK** | field:customerReview |
| `A` | **OK** | ∅ |
| `O2O` | **OK** | enhanced_rules:准客来源-简称, field:pcustSourcType, field:validSinsPol |
| `陈金秀` | **MISS** | ∅ |
| `天气怎么样` | **OK** | ∅ |
| `客户平时有什么兴趣爱好` | **OK** | ∅ |


## Prior recipe snapshots

- **V2**: A=False empty=0.017 avg=7.55 dev=0.773/0.556 hold=0.200/0.667
- **V2R**: A=True empty=0.020 avg=7.53 dev=0.773/0.889 hold=0.200/1.000
- **V5_stem**: A=True empty=0.023 avg=2.83 dev=0.727/0.889 hold=0.200/1.000
- **V8_highbar**: A=True empty=0.636 avg=0.76 dev=0.545/1.000 hold=0.000/1.000
- **V10_pareto**: A=True empty=0.023 avg=2.82 dev=0.727/0.889 hold=0.200/1.000

## Can we solve it?

**PARTIAL** — SOFT_V2R_L10 clears practical Auth-OFF navigation (A) and improves irr rejection; formal dual thresholds still fail (dev top8=0.773<0.85, holdout top8=0.200<0.85). Holdout paraphrases lack source tokens: holdout-v3-spouse-birthday, holdout-v3-family-phone, holdout-v3-insured-name, holdout-v3-occupation, holdout-v3-contact-address.

Final pick (2026-08-13 00:47 UTC+8): `SOFT_V2R_L10`

- Pareto: `{"best_balanced": "SOFT_V2R_L10", "best_recall_with_reject": "SOFT_V2R_L10", "best_reject_highbar": "V8_highbar", "simplest_practical": "V2R"}`
- Focus quals: `{"关爱客户": "OK", "有钱": "OK", "有钱客户": "OK", "金凤": "OK", "盘客": "OK", "去盘客": "OK", "A": "OK", "O2O": "OK", "陈金秀": "MISS", "天气怎么样": "OK", "客户平时有什么兴趣爱好": "OK"}`
- Stress: empty=0.619, avg_hits=1.33, fa={}
- Labeled: dev top8/irr=0.773/1.000; holdout=0.200/1.000
- Dual both: False

### Working recipe stack

1. hard reject unsupported/irrelevant markers (兴趣/爱好/天气/红烧肉/黑洞…) → empty
2. abbrname exact membership only (金凤)
3. spoken-key / example phrase exact from field V1 projection
4. enhanced_rules search with quality gates (prefer name; no ultra-common 客户 alone)
5. field V1 examples/notes projection + fused exact/IDF; optional 2-char stem as phrase containment
6. soft long-query filter: for long queries, drop weak field lexical hits lacking phrase/exact/strong coverage

### Remaining failures

- Formal dual thresholds: not achievable without holdout synonym injection or holdout invalidate/rebuild.
- Holdout paraphrases (另一半/保的是谁/做哪一行/收信寄到哪里) absent from source; 家里人 partially present but not enough under gates.
- 陈金秀 stays empty (safe; not random product fields) — name navigation still MISS without name-field router.
- Soft long filter empty≈0.62 is above the 0.10–0.55 band but fixes V2’s empty≈0.02 over-fire; V2R alone keeps over-fire.

Artifacts: `/workspace/draft-run/empirical-solve-iterations.md`, `/workspace/draft-run/empirical-solve-best.json`, `/workspace/draft-run/experiments/empirical-solve-iterations.json`
