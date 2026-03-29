# MAE v1：Agent Framework & Visible Collaboration Template

> Status: draft v1  
> Updated: 2026-03-29  
> Purpose: 将当前多 Agent 系统从“后台编排”升级为“用户可见、可审计、可介入”的 MAE 协作系统。

---

## 1. 背景

当前系统已经具备以下基础：
- 多 Agent 角色（Andrew / Rex / Lulu / Alex）
- OpenClaw 作为统一运行时
- ACP 作为 agent 调用与切换协议
- Dashboard 作为状态可视化面板
- GitHub / Feishu / Airtable 作为外部承载与协作层

但当前仍存在两个核心问题：
1. **Agent 框架未被重新整理清楚**：角色边界、交付边界、协作协议仍不够统一。
2. **Agent-to-Agent 协作过于隐性**：大量交互发生在 internal sessions 中，用户不可见、不可审计、不可直接介入。

因此，MAE v1 的目标是：
> 把现有多 Agent 系统梳理成一套“结构清楚 + 协作显性 + 可被用户旁观和纠偏”的执行框架。

---

## 2. 本轮两个核心任务

### Task A：现有 Agent Framework 再整理

目标：把现有 Agent 系统重新梳理清楚，明确职责、输入、输出、交接方式与系统边界。

#### 需要回答的问题
- Andrew / Rex / Lulu / Alex 分别负责什么？
- MAE / ACP / Dashboard / OpenClaw 分别扮演什么角色？
- 什么属于后台自动执行？什么必须对用户可见？
- 什么交付写 GitHub？什么写 Feishu？什么写 Airtable / Dashboard？
- Agent-to-Agent 的 handoff 应该如何标准化？

#### 预期交付物
1. **Agent 系统结构图**
2. **角色职责说明**
3. **交付边界说明**
4. **Agent-to-Agent 协作协议 v1**

---

### Task B：建立 Feishu 显性协作群

目标：让一部分 Agent-to-Agent 协作从“隐性 session”迁移到“用户可见的 Feishu 群组”。

#### 设计原则
- 不是把所有内部消息都公开，而是只公开“关键协作节点”
- 用户应能看到：任务锁定、进度 heartbeat、BLOCKED、DONE、handoff
- 用户应能在群里直接插话、纠偏、补充要求

#### Feishu 群推荐消息类型
1. **任务锁定消息**
2. **15–30 分钟 Heartbeat**
3. **BLOCKED 报告**
4. **DONE 汇报**
5. **关键 Handoff**
6. **需用户拍板的决策节点**

#### 预期交付物
1. 一个 Feishu 群组
2. 一版 Agent 群内发言规范
3. 一版可复用消息模板
4. 一版“显性 vs 隐性协作”边界定义

---

## 3. 建议的系统结构（v1）

### 3.1 角色分工

| Agent | 角色定位 | 主职责 | 典型输出 |
|------|----------|--------|---------|
| Andrew | 学习 / 框架整理 / 协议沉淀 | 学习、结构化整理、方法论、流程定义 | 学习卡片、框架文档、协议草案 |
| Rex | 工作推进 / CER / 项目执行 | 项目推进、风险跟踪、任务落地、商业与工程推进 | 周报、风险清单、推进方案 |
| Lulu | 输出生产 / 内容表达 | 选题、脚本、长文稿、公众号、视频文案 | 笔记、文章、脚本、成稿 |
| Alex | Personal / 情绪关系 / 生活运营 | Journal、情绪、关系、成长支持 | 复盘、计划、动作卡 |

### 3.2 系统组件角色

| 系统组件 | 角色 |
|---------|------|
| OpenClaw | 统一运行时与对话入口 |
| ACP | Agent 调用协议 |
| MAE | 多 Agent 执行框架（任务流转 / 生命周期） |
| Dashboard | 可视化状态板 |
| Airtable | 任务真源 / 状态存储 |
| GitHub | 代码 / 文档 /版本化交付 |
| Feishu | 文档协作 / 用户可见协作 / 显性交流 |

---

## 4. 显性协作与隐性协作边界

### 应保留为隐性 session 的内容
- 高频内部推理
- 中间草稿协商
- 临时调试和试错
- 大量碎片化 agent 内部调度

### 应迁移到显性群的内容
- 任务锁定
- 关键 handoff
- 进度 heartbeat
- BLOCKED
- DONE 汇报
- 需要用户拍板的重大决策

> 原则：**不是所有协作都公开，而是关键状态必须公开。**

---

## 5. 群消息模板（建议）

### 5.1 任务锁定
```text
✅ 任务已锁定
任务ID: <id>
负责人: <agent>
目标: <一句话>
ETA: <时间>
下一次汇报: <时间>
```

### 5.2 Heartbeat
```text
🟡 Heartbeat
任务ID: <id>
当前步骤: <step>
已完成: <summary>
阻塞: <if any>
下一步: <next>
下一次汇报: <time>
```

### 5.3 BLOCKED
```text
🔴 BLOCKED
任务ID: <id>
阻塞原因: <reason>
需要支持: <what is needed>
恢复方案: <recovery path>
```

### 5.4 DONE
```text
✅ DONE
任务ID: <id>
结果: <summary>
证据: <GitHub/Feishu/link>
后续建议: <next>
```

### 5.5 Handoff
```text
🔁 HANDOFF
任务ID: <id>
From: <agent>
To: <agent>
交接内容: <summary>
当前状态: <state>
注意事项: <notes>
```

---

## 6. 推荐推进顺序

### Step 1
先完成 **Agent Framework 梳理**，确保角色、交付边界、系统关系清楚。

### Step 2
再建立 **Feishu 显性协作群**，并只把关键协作节点迁移进去。

### Step 3
把 Dashboard / Airtable / GitHub / Feishu 的写回关系统一起来。

---

## 7. 一句话总结

> MAE v1 不是再增加更多 Agent，而是把现有多 Agent 系统整理成一套：**角色清楚、协作显性、用户可见、可持续演进** 的执行框架。
