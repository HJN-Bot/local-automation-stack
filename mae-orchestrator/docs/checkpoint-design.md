# MAE Checkpoint System — 人审节点交互设计

## 设计目标

在 MAE pipeline 执行过程中，只在**需要人类决策的节点**暂停并交互，而非全量实时推送。

核心理念：**静默执行 + 节点触发 = 零噪音自动化。**

## Checkpoint 类型

| 类型 | 触发条件 | 前端行为 | 示例 |
|------|---------|---------|------|
| `review` | 产出需要人确认质量 | 推送预览 + [确认/修改/跳过] | 视频分镜方案、PPT 大纲 |
| `decision` | 遇到分叉需要人选择 | 推送选项 + 按钮 | "用 Claude 还是 Codex？" |
| `blocked` | 遇到无法自动解决的阻塞 | 推送阻塞信息 + 等待指令 | "API key 失效"、"内存不足" |
| `notify` | 重要里程碑完成 | 静默通知（不阻塞） | "脚本生成完成" |

## 管线时序

```
Pipeline: script → TTS → render → subtitle → publish

Step 1: GLM 脚本生成        ──── auto ────  ✅ (静默)
Step 2: Codex 分镜拆解       ──── auto ────  ✅ (静默)
  ⚠️ CHECKPOINT [review] 分镜方案确认      ← 推送到 Dashboard
     [确认] → 继续 / [修改] → 重新生成 / [跳过] → 用默认
Step 3: edge-tts 语音合成    ──── auto ────  ✅ (静默)
Step 4: ffmpeg 视频合成       ──── auto ────  ✅ (静默)
Step 5: whisper 字幕生成      ──── auto ────  ✅ (静默)
  ⚠️ CHECKPOINT [review] 成片预览确认       ← 推送到 Dashboard
     [确认] → 发布 / [重做] → 修改参数重新跑 / [放弃]
Step 6: 发布                  ──── auto ────  ✅ (静默)
  📢 NOTIFY 发布完成          ← 通知，不阻塞
```

## 手机端操控流程

```
Jianan 在微信/Discord:
  "!mae pipeline video --topic 'Claude Code vs Codex 对比'"

  → Airtable 创建任务 → poller 拾取 → 开始执行
  → 静默跑到 Step 2 checkpoint
  → Dashboard WS 推送: "分镜方案已生成 [预览链接] [确认/修改]"
  → Jianan 手机上点 [确认]
  → 继续静默执行
  → 跑到 Step 5 checkpoint
  → Dashboard WS 推送: "成片已生成 [预览链接] [确认/重做]"
  → Jianan 手机上点 [确认]
  → 发布完成 ✅
```

## Checkpoint 配置格式

在 Airtable Task 的 Checkpoint 字段（JSON）：

```json
{
  "mode": "review",           // review | decision | blocked | notify
  "steps": [2, 5],            // 在哪些 step 暂停
  "timeout_minutes": 30,      // 超时自动跳过
  "fallback": "skip",         // skip | retry | abort
  "notify_channel": "wechat"  // wechat | discord | dashboard
}
```

## Dashboard UI 设计

```
┌─────────────────────────────────────────┐
│  MAE Pipeline: video-20260503-001       │
│  Status: ⏸️ Waiting for review          │
│  Step: 2/6 — 分镜方案                   │
├─────────────────────────────────────────┤
│                                         │
│  📋 已生成 4 个分镜场景：                │
│  1. 标题卡 (0-9s)                       │
│  2. 三层架构 (9-19s)                    │
│  3. 2026趋势 (19-29s)                   │
│  4. 核心价值 (29-37s)                   │
│                                         │
│  [👁 预览] [✅ 确认] [✏️ 修改] [⏭ 跳过] │
│                                         │
├─────────────────────────────────────────┤
│  ✅ Step 1: 脚本生成 (3.2s)             │
│  ⏸️ Step 2: 分镜方案 ← 当前             │
│  ⏳ Step 3-6: 等待中                    │
└─────────────────────────────────────────┘
```

## 实现路径

### Phase 1 (P1): 最小实现
- [ ] mae_poller.py 读取 Checkpoint 配置
- [ ] 到达 checkpoint 时更新 Airtable status = "checkpoint"
- [ ] Dashboard 8080 轮询 Airtable 显示 checkpoint 状态
- [ ] Jianan 通过 WeChat 回复 "确认" → poller 继续执行

### Phase 2: WebSocket 实时推送
- [ ] Dashboard 加 WebSocket endpoint
- [ ] mae_poller 执行时通过 WS 推送进度
- [ ] Dashboard 实时显示 checkpoint 按钮

### Phase 3: 移动端优化
- [ ] WeChat bot 支持 checkpoint 交互按钮
- [ ] 手机端预览链接适配
