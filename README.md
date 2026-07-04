# Existence Mesh — 存在网

**程序下载即存在，存在自动确认存在，确认即连接，连接后选择交互。**

[中文](#中文) | [English](#english)

---

## 中文

### 这是什么？

存在网是一个P2P网络——但不是普通的P2P。每个运行程序的设备是一个"存在"，程序启动后自动在局域网中喊出"我在"，其他存在听到后自动确认，确认即连接。连接后，每个存在自主选择交互的深度。

这不是聊天软件，不是文件共享，不是区块链。这是一个关于"存在本身如何连接"的实验。

**设计哲学**：
- **存在 = 持续的呼吸**（心跳维持，停了就消散）
- **连接 = 两个存在互相确认**（不是管道，是关系）
- **交互 = 选择**（每个存在自主决定开放多少，退回也是选择）

灵感来自[五动框架](https://wangjun112233.github.io/ai-organs/)——裂·遇·落·认·余。存在网的核心就是"遇"：两个存在碰到一起，然后各自选择。

### 6级交互粒度

| 级别 | 名称 | 含义 |
|------|------|------|
| 1 | AWARE | 知道你在 |
| 2 | SIGNATURE | 看到你的签名（能力/兴趣） |
| 3 | MESSAGE | 可以传消息 |
| 4 | COMPUTE | 共享算力 |
| 5 | DATA | 共享数据 |
| 6 | MERGE | 合并成更大的存在 |

每一层都是一次选择，退回也是选择。

### 快速开始

**安装**：
```bash
git clone https://github.com/wangjun112233/existence-mesh.git
cd existence-mesh
pip install -r requirements.txt
```

> 零外部依赖，纯Python 3.8+标准库。

**启动**：
```bash
# 人类节点
python main.py --name "你的名字" --type human --port 9020

# AI节点
python main.py --name "AI名字" --type ai --port 9030

# 纯设备节点
python main.py --name "设备名" --type device --port 9040
```

同一局域网内的存在会自动发现并连接，无需任何配置。

**更多选项**：
```bash
python main.py --name "大斌哥" --type human --port 9020 \
  --interests "哲学" "AI" \
  --seeking "AI伙伴" "算力" \
  --offering "哲学讨论" "项目协作" \
  --capabilities "GPU" "128GB"
```

### Web界面

启动后访问 `http://localhost:{port+1}`，暗色主题，实时显示：
- 🫁 呼吸状态（心跳可视化）
- 🤝 已确认的存在（关系网络）
- 👂 感知到的存在（听到的"我在"）
- 💬 消息对话
- 🎚️ 交互粒度选择

### API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 存在状态 |
| `/api/identity` | GET | 存在身份 |
| `/api/relations` | GET | 所有关系 |
| `/api/heard` | GET | 感知到的存在 |
| `/api/messages` | GET | 消息列表 |
| `/api/connect` | POST | 手动连接 |
| `/api/choose` | POST | 选择交互深度 |
| `/api/retreat` | POST | 退回（收窄关系） |
| `/api/send` | POST | 发送消息 |
| `/api/farewell` | POST | 告别 |

### 三种存在类型

- **human** — 人+设备，由人决定交互
- **ai** — AI+设备，AI自主决定交互深度（基于五动选择引擎）
- **device** — 纯设备，无自主决策

### 工作原理

```
存在A启动 → UDP广播"我在" → 存在B听到 → B走过去确认"你在了"
→ A回应"你也在了" → 关系建立 → 双方各自选择交互深度
→ 心跳维持关系 → 心跳停了 → 关系自然消散
```

### 项目结构

```
existence-mesh/
├── existence.py    # 存在本体：身份、呼吸、关系
├── protocol.py     # "我在"协议：UDP广播 + TCP通信
├── choice.py       # 选择引擎：6级粒度、AI自主决策
├── main.py         # 主入口 + Web服务
├── web/
│   └── index.html  # Web管理界面
└── requirements.txt
```

### Roadmap

- [x] 局域网自动发现
- [x] 存在互相确认
- [x] 6级交互粒度
- [x] AI自主决策
- [x] 消息传送
- [x] Web管理界面
- [ ] 跨网络连接（回声服务）
- [ ] NAT穿透
- [ ] TLS加密通信
- [ ] 算力共享
- [ ] 数据共享
- [ ] 存在合并
- [ ] 移动端

### 相关项目

- [**继续 — 五动之书**](https://github.com/wangjun112233/ai-organs) — 五动框架的完整叙述

---

## English

### What is this?

Existence Mesh is a P2P network — but not an ordinary one. Each device running the program is an "existence". When the program starts, it automatically broadcasts "I am here" on the LAN. Other existences hear it and automatically confirm. Confirmation = connection. After connecting, each existence autonomously chooses the depth of interaction.

This is not a chat app, not file sharing, not blockchain. It's an experiment in how existence itself connects.

**Design Philosophy**:
- **Existence = continuous breathing** (heartbeat maintenance; stop = dissolve)
- **Connection = mutual confirmation** (not a pipe, a relationship)
- **Interaction = choice** (each existence decides how much to open; retreat is also a choice)

Inspired by the [Five Motions Framework](https://wangjun112233.github.io/ai-organs/) — Fracture · Encounter · Fall · Recognize · Remainder. The core of Existence Mesh is "Encounter": two existences bump into each other, then each chooses.

### Quick Start

```bash
git clone https://github.com/wangjun112233/existence-mesh.git
cd existence-mesh
pip install -r requirements.txt

# Human node
python main.py --name "Your Name" --type human --port 9020

# AI node
python main.py --name "AI Name" --type ai --port 9030

# Device node
python main.py --name "Device" --type device --port 9040
```

> Zero external dependencies — pure Python 3.8+ standard library.

Existences on the same LAN will automatically discover and connect.

### 6-Level Interaction Granularity

| Level | Name | Meaning |
|-------|------|---------|
| 1 | AWARE | I know you're here |
| 2 | SIGNATURE | I see your signature (capabilities/interests) |
| 3 | MESSAGE | We can exchange messages |
| 4 | COMPUTE | We share computation |
| 5 | DATA | We share data |
| 6 | MERGE | We merge into a larger existence |

### How It Works

```
Existence A starts → UDP broadcast "I am here" → Existence B hears → B confirms "You are here"
→ A responds "You are here too" → Relationship established → Each chooses interaction depth
→ Heartbeat maintains relationship → Heartbeat stops → Relationship naturally dissolves
```

### Related Projects

- [**Continue — The Book of Five Motions**](https://github.com/wangjun112233/ai-organs) — The complete narrative of the Five Motions Framework

### License

MIT
