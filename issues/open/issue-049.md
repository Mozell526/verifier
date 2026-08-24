# Issue #049: 源头互搏在提示里的裸词四句，必须删掉，不得再贴一张贴纸

**Class**: architecture
**Severity**: high
**Status**: verifier-raised
**Evidence**: code-analysis
**Layer**: draft judge host
**Cases**: `impl/projects/client_search/draft/judge.py` 原 L1504–1508；王坤林过严

## Verifier Discovery

045 Consensus：源头仍在 draft judge 提示里的裸词四句。它要求目录级「独立姓名证据」，
和 1A「2–4 字中文名可单独撑姓名维」互搏。王坤林过严从这里来。
check 的 c) 条：只改内存对照、不改这句，下次重跑 judge 仍过严。

用户本轮打开了 host：构建 judge 实现。本 issue 只审源头这一刀。

已做：

- 删除 `### 裸词规则` 标题和后面四句姓名闸
- 留下 inlive 操作符 / match_mode 那句（不是姓名闸）
- 没有把 `decide_sufficiency` / `decide_object_cover` / 残句代数写进 prompt
- 对应测试改为断言裸词闸不在系统提示里

```bash
python3 -c "from pathlib import Path; t=Path('impl/projects/client_search/draft/judge.py').read_text(); assert '### 裸词规则' not in t; assert '独立姓名证据' not in t; assert 'inlive 空间列出的操作符或 match_mode 只证明可达' in t; assert 'decide_object_cover' not in t; print('049 host prompt gate gone')"
```

## 可证伪

1. 若 `### 裸词规则` 或「独立姓名证据」还在 draft judge 提示里，本 issue 未修。
2. 若删掉之后又贴了一段「这是姓名题所以怎样」或把充分性函数名写进 prompt，本 issue 未修。
3. 若 inlive 操作符那句被误删，本 issue 过删。

## 请对手挑战

- 删四句是不是只改了展示、判定源头其实还在别的提示段？
- 剩下的「一级证据即可支撑 fulfilled」会不会在充分性没打中时把假名放成 F？
  （若会，那是 050 的事：代码必须在打中时说话，不是再写提示。）
- 045 说不得把充分性并进提示。本次并进的是代码口，不是提示。若你认为代码口本身就越权，写在 050 / 051。

不要重开 042–045 的对错。不要代选昊轩必须成功。
