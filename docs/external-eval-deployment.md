# 外网评测部署：远程 verifier + 本地业务系统（SSH 反向隧道）

适用场景：verifier 部署在一台外网服务器上，被测业务系统跑在使用者本机（或使用者能触达的机器）。
使用者侧**零安装**：只需要系统自带的 ssh 客户端，粘贴一条命令。

## 拓扑

```
使用者本机                                外网服务器
┌──────────────────────┐                ┌──────────────────────────────┐
│ 业务系统 127.0.0.1:8000 │                │ verifier  127.0.0.1:8022      │
│ 浏览器 → localhost:18080│ ←── ssh ────→ │ 隧道口    127.0.0.1:15001     │
└──────────────────────┘   一条长连接    │ sshd     0.0.0.0:22          │
                                        └──────────────────────────────┘
```

一条 ssh 连接同时承载两个方向：
- `-R`：业务系统被"搬到"服务器的 `127.0.0.1:15001`，verifier 像调本机服务一样调它；
- `-L`：verifier 前端被"搬到"使用者本机的 `localhost:18080`，浏览器直接访问。

verifier 与隧道口都只绑服务器 loopback，**服务器上没有任何公网暴露的 HTTP 端口**，
因此现阶段无需给 verifier 加鉴权。

## 核查结论：评测代码零改动

- 真实请求唯一出口是 `impl/core/live_transport.py` 的 `LiveTransport`，llm_probe 的
  `resolve_http` 只校验 scheme 为 http/https，case 信封本来就接受任意 URL——
  填 `http://127.0.0.1:15001/...` 即走隧道，RealLive 真实性不变量原样成立。
- 前端全部同源相对路径挂在 `/frontend`，经 `-L` 转发访问无任何地址假设问题。
- `impl/config.yaml` server 默认绑 `127.0.0.1:8022`，保持不动。
- judge/attribute 走 OpenAI 兼容端点（.env 的 `LLM_BASE_URL`），与隧道无关。

## 服务器侧一次性准备

### 1. 部署 verifier

```bash
# Python 3.11
python3.11 -m venv ~/verifier-venv && source ~/verifier-venv/bin/activate
pip install -r requirements.txt
```

`.env` 最小配置（参照 impl/config.yaml environment 节）：

```
DEEPSEEK_API_KEY=...            # 或所用网关的 key
LLM_BASE_URL=...                # judge 用的 OpenAI 兼容端点，须从该服务器可达
LLM_MODEL=...
EMBEDDING_ENABLED=false         # 或配 BAILIAN_API_KEY
```

**部署时必须验证**：当前 .env 用的 LLM 网关（如 ai.ainsv.com）从这台服务器是否可达。
不可达就换成从公网可达的端点（DeepSeek 官方 API 等）。验证方式：

```bash
bash run.sh config-check
curl -s $LLM_BASE_URL/models -H "Authorization: Bearer $KEY" | head
```

启动（保持默认 127.0.0.1 绑定，不要改成 0.0.0.0）：

```bash
bash run.sh server
```

### 2. 建隧道账号并加固 sshd

```bash
sudo useradd -m -s /usr/sbin/nologin eval-tunnel
sudo passwd eval-tunnel        # 或配 authorized_keys，推荐密钥
```

`/etc/ssh/sshd_config` 追加（然后 `sudo systemctl reload sshd`）：

```
Match User eval-tunnel
    AllowTcpForwarding yes
    PermitListen 15001 15002 15003
    PermitOpen 127.0.0.1:8022
    PermitTTY no
    X11Forwarding no
    AllowAgentForwarding no
    ForceCommand /bin/false
```

要点：
- 该账号不能开 shell、不能执行命令，只能建隧道；
- `PermitListen` 限死反向隧道可用端口（每个使用者固定一个：15001/15002/…）；
- `PermitOpen` 限死正向转发只能指向 verifier 前端；
- sshd 默认 `GatewayPorts no`，`-R` 端口只绑服务器 loopback，公网碰不到隧道口。

若使用者网络封锁出站 22 端口，让 sshd 追加监听 443：`Port 22` + `Port 443`。

## 使用者接入（唯一要做的事）

```bash
ssh -N -o ServerAliveInterval=30 \
    -R 15001:127.0.0.1:8000 \
    -L 18080:127.0.0.1:8022 \
    eval-tunnel@<服务器地址>
```

- `8000` 换成本地业务系统实际端口；`15001` 用分配给自己的端口；
- 评测期间保持该终端开着；断了重跑一遍即可；
- 浏览器访问 `http://localhost:18080` 即 verifier 前端。

评测目标地址填隧道口，两种方式任选：

case 信封里直接给 url：

```json
{ "url": "http://127.0.0.1:15001/api/v1/xxx", "method": "POST", "body": { ... } }
```

或在 `impl/projects/llm_probe/capability_map.yaml` 加预设：

```yaml
my_local_service:
  capability: |
    （能力口径描述）
  service:
    url: http://127.0.0.1:15001/api/v1/xxx
    method: POST
    timeout_seconds: 60
  mock_body:
    user_text: '{query}'
```

## 当前部署实例(2026-08-28)

- 服务器:`154.9.252.35`(Debian 11,与 llm_client_search/livekit 等服务共存)
- 代码:`/opt/verifier`,Python 3.11.16 venv 于 `/opt/verifier/venv`
- 服务:`systemctl {status,restart} verifier`(开机自启,绑 `127.0.0.1:8022`)
- 隧道账号:`eval-tunnel`(密钥登录,已装入部署机的公钥;不能开 shell)
- 已验证:LLM 网关可达;端到端评测(隧道→本地 mock API→judge)judge 判定 fulfilled

接入命令:

```bash
ssh -N -o ServerAliveInterval=30 \
    -R 15001:127.0.0.1:8000 \
    -L 18080:127.0.0.1:8022 \
    eval-tunnel@154.9.252.35
```

浏览器访问 `http://localhost:18080`,评测目标填 `http://127.0.0.1:15001/...`。

## 多人共用

每人固定一个隧道端口（15001/15002/15003，需在 `PermitListen` 中放行），
case/预设里各用各的端口。当前部署形态是单实例共用一个 verifier，
case pool 等数据不隔离，适合小团队探索用途；需要隔离时再考虑每人一实例。
