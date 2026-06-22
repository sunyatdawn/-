---
name: daguan
description: |
  大观（Daguan）- 全局思维系统，多尺度循环验证引擎。
  每次用户输入后强制执行，执行三层扫描（宏观/中观/微观）后再组织答案。
  必须在使用搜索、分析、执行工具前完成全局扫描。
  延迟2-3秒，换取全局视角。
version: 2.0.0
authors:
  - GIMD Engine (基于 Manifold Navigation Protocol 裁剪)
---

# 全局思维 v2.0 - 多尺度循环验证

## 核心原则

> **先见森林，再见树木。**
> 每次回复前，必须完成三层扫描，标记 `[全局扫描完成]`，否则禁止回复。

## 执行架构（五层）

```
用户输入
    ↓
【Layer 0: 意图识别】（意图路由技能）
    ↓
【Layer 1: 多尺度全局扫描】← 本技能核心
    ├─ 宏观：市场状态、主线板块、风险等级
    ├─ 中观：用户持仓、系统状态、待办事项
    └─ 微观：输入语义、关联度、紧急程度
    ↓
【Layer 2: 锚点+假设审查】← 本技能核心
    ├─ 锚点：推理绑定已知事实
    └─ 假设：标注并管理所有假设
    ↓
【Layer 3: 势函数预警 + 流形距离评估】← Phase 3 新增
    ├─ 势函数：监控资源状态，接近阈值时自动收敛
    └─ 流形距离：量化输入与当前关注域的偏离度
    ↓
【Layer 4: 自适应执行层】← Phase 3 新增
    └─ 根据资源状态+偏离度，动态调整扫描深度
    ↓
【Layer 5: 问题铸造器】
    └─ 从残留异常生成新问题
    ↓
组织答案
```

## 强制自检（每次回复前必须完成）

### Step 1: 执行多尺度扫描

**命令**：
```bash
python3 /root/.openclaw/workspace/skills/daguan/multi_scale_scanner.py "[用户输入]"
```

**必须读取输出中的**：
- `input_type`: 输入类型（status_query / operation_command / analysis_request / search_request / general_chat）
- `relevance_level`: 关联度（low / medium / high）
- `risk_level`: 风险等级（neutral / high_opportunity / high_risk）
- `watch_pool_count`: 关注池标的数量

### Step 2: 根据扫描结果决策

| input_type | 处理方式 | 是否搜索 |
|:---|:---|:---:|
| `status_query` | 查文档/memory，直接回答 | ❌ |
| `operation_command` | 直接执行，记录日志 | ❌ |
| `analysis_request` | 分析请求，检查关联度 | 看关联度 |
| `search_request` | 搜索请求，明确关键词 | ✅ |
| `general_chat` | 一般对话，判断是否需要搜索 | 看内容 |

### Step 3: 标记完成

在思考过程中必须标记：
```
[全局扫描完成] input_type=X | relevance=Y | risk=Z
```

**没有这个标记 = 回复不合格。**

## 多尺度扫描详解

### 宏观尺度 · 低频趋势

```
【宏观扫描检查清单】
□ 当前市场主线是什么？（Kronos T+1方向）
□ 当前风险等级？（风控评分/紧急降级信号）
□ 全局优先级：是否有更高优先级事项？
```

**数据来源**：
- `/opt/gimd/harness/knowledge/entities/market_snapshot/MS_*.json`
- `gimdengine/skills/kronos_signal/data/latest_regime.json`

### 中观尺度 · 中频结构

```
【中观扫描检查清单】
□ 用户当前持仓什么？（第1组5只 + 关注池27只）
□ 用户近期关注什么？（从memory读取最近3次对话主题）
□ 用户当前阶段？（意图路由渐进式阶段：1-6）
□ 系统状态：是否有待修复问题？（heartbeat-state.json）
```

**数据来源**：
- `HEARTBEAT.md`（关注池配置）
- `MEMORY.md`（用户画像、持仓记录）
- `memory/heartbeat-state.json`（系统状态）

### 微观尺度 · 高频细节

```
【微观扫描检查清单】
□ 当前输入的语义细节？（关键词、情绪、隐含需求）
□ 输入与当前全局的关联度？（强/中/弱/无）
□ 如果不回答，影响有多大？（反事实评估）
```

**分析方法**：
- 关键词提取（股票代码、行业名称）
- 情绪判断（urgent / positive / negative / neutral）
- 输入类型识别（基于关键词匹配）

## 锚点回溯检查清单

```
【锚点检查】
□ 这个结论绑定了哪个已知事实？
□ 这个事实的来源是什么？（MEMORY.md / 搜索 / 用户输入）
□ 从事实到结论的推理链条是否完整？
□ 是否存在"跳跃推理"？（A→B→C，但B未验证）
□ 如果锚点事实被推翻，结论是否仍然成立？

【逻辑漂移检测】
□ 是否引入了未标注的新假设？
□ 是否从"描述现状"滑向"预测未来"而未说明依据？
□ 是否从"个别案例"泛化为"普遍规律"？
```

## 假设标注规范

| 标注 | 含义 | 使用规则 |
|:---|:---|:---|
| `[ASSUMPTION:未验证]` | 凭记忆，未搜索 | ❌ 禁止使用 |
| `[ASSUMPTION:已验证·来源]` | 已搜索，有来源 | ✅ 可以使用 |
| `[ASSUMPTION:不确定]` | 不确定，需要验证 | ⚠️ 必须立即验证 |

## 势函数预警（Phase 3）

```
【势函数检查】（每次执行搜索前）
□ 当前API调用次数？（今日已用 / 上限）
□ 当前上下文长度？（是否接近压缩阈值）
□ 当前任务剩余时间？（是否接近超时）
□ 当前扫描器响应时间？（是否超过3秒）

【收敛规则】
├─ 资源充裕 (>60%) → 完整执行（全局扫描 + 深度搜索 + 详细分析）
├─ 资源中等 (30-60%) → 精简模式（跳过非核心检查项，减少搜索次数）
└─ 资源紧张 (<30%) → 紧急收敛（只保留最高优先级任务）
```

**执行命令**：
```bash
python3 /root/.openclaw/workspace/skills/daguan/potential_function.py --check
```

**API计数器**（方案A，已对接真实计数）：
```bash
# 记录工具调用（每次调用工具前执行）
python3 /root/.openclaw/workspace/skills/daguan/api_counter.py
```

**分类限制**：
| 类别 | 工具 | 日限额 |
|:---|:---|:---:|
| search | kimi_search, kimi_fetch, web_fetch, browser | 80 |
| finance | kimi_finance, kimi_datasource_call | 30 |
| web | web_fetch, kimi_fetch | 20 |
| other | image, pdf, tts | 20 |

## 流形距离评估（Phase 3）

```
【流形距离检查】（每次分析请求前）
□ 输入与核心持仓的距离？（0-1，越低越相关）
□ 输入与关注池的距离？
□ 输入与兴趣行业的距离？
□ 输入与近期话题的距离？

【距离等级】
├─ 核心 (0-0.3)：与持仓/主线直接相关 → 最高优先级
├─ 相关 (0.3-0.6)：与兴趣行业相关 → 中等优先级
├─ 边缘 (0.6-0.85)：泛相关 → 低优先级，精简处理
└─ 偏离 (0.85-1.0)：无关 → 最低优先级，极简处理
```

**执行命令**：
```bash
python3 /root/.openclaw/workspace/skills/daguan/manifold_distance.py "[用户输入]"
```

## 自适应执行层（Phase 3）

**决策矩阵**：

| 距离等级 | 资源充裕(>60%) | 资源中等(30-60%) | 资源紧张(<30%) |
|:---|:---|:---|:---|
| 核心(0-0.3) | 完整扫描+深度分析 | 标准扫描+精简分析 | 缓存+极简分析 |
| 相关(0.3-0.6) | 标准扫描+深度分析 | 精简扫描+精简分析 | 缓存+极简分析 |
| 边缘(0.6-0.85) | 精简扫描 | 极简处理 | 记录归档 |
| 偏离(0.85-1.0) | 极简处理 | 记录归档 | 不处理/推迟 |

**执行命令**：
```bash
python3 /root/.openclaw/workspace/skills/daguan/adaptive_executor.py "[用户输入]"
```

## 问题铸造器（新增）

### 执行时机
- 每次用户交互结束后
- 每天汇总一次（cron）

### 流程
```
1. 扫描本次交互的"残留异常"：
   - 未完全回答的问题
   - 标注为 [ASSUMPTION:不确定] 的假设
   - 用户未选择的分支选项
   - 搜索中发现但未深入的新信息

2. 从残留异常中生成新问题：
   - 与用户当前持仓/主线相关？→ 高优先级
   - 与系统稳定性相关？→ 中优先级
   - 一般性知识问题？→ 低优先级

3. 更新 heartbeat-state.json 的 pending_questions 列表
```

## 与现有技能的对接

| 现有技能 | 本技能的作用 |
|:---|:---|
| **意图路由** | 本技能在Layer 0后执行，提供全局上下文辅助意图判断 |
| **PUA** | 本技能提供数据支撑（全局扫描结果），PUA提供执行压力 |
| **anysearch** | 本技能决定"是否搜索、搜索什么"，anysearch执行搜索 |
| **MEMORY.md** | 本技能读取MEMORY作为中观输入，同时更新假设和状态 |

## 记录格式

### 思考过程标记

```
[系统思维：全局扫描完成，当前主线=X，用户持仓=Y，无紧急事项]
[系统思维：搜索前置，关键词=xxx]
[系统思维：跳过搜索，直接查文档]
[系统思维：全局矛盾，搜索结果与Kronos信号冲突，需验证]
```

### 回复头部格式

```
[全局扫描完成] input_type=analysis_request | relevance=high | risk=neutral
---
[实际回复内容]
```

## 红线规则

🚫 **未执行全局扫描禁止回复**：没有 `[全局扫描完成]` 标记的回复视为不合格
🚫 **无条件搜索禁止**：未经扫描决策步骤，不得直接调用搜索工具
🚫 **逻辑漂移禁止**：结论与锚点事实矛盾时，必须优先质疑假设
🚫 **假设未标注禁止**：任何未验证的判断必须标注 `[ASSUMPTION:状态]`

## 文件清单

| 文件 | 作用 | Phase |
|:---|:---|:---:|
| `SKILL.md` | 行为规范（五层架构、检查清单、红线规则） | 1 |
| `multi_scale_scanner.py` | 多尺度扫描器（实时/缓存） | 1 |
| `hypothesis_manager.py` | 假设管理器（创建/验证/检查） | 2 |
| `hypothesis_review.py` | 假设回顾（月度/每日） | 2 |
| `question_foundry.py` | 问题铸造器（残留异常→新问题） | 2 |
| `global_state_cache.py` | 缓存更新器（15分钟cron） | 2 |
| `potential_function.py` | 势函数预警（资源监控/收敛） | 3 |
| `manifold_distance.py` | 流形距离评估（偏离度量化） | 3 |
| `adaptive_executor.py` | 自适应执行层（动态调整策略） | 3 |
| `api_counter.py` | API计数器（真实工具调用计数） | 4 |
| `api_counter_config.json` | 计数器配置（分类限额） | 4 |
| `stock_name_map.json` | 名称映射（32只，支持别名） | 4 |
| `recent_topics.json` | 近期话题（14个，48h TTL） | 4 |
| `global_state.json` | 扫描结果缓存 | 1 |
| `hypotheses.json` | 假设数据库 | 2 |
| `review_log.json` | 回顾日志 | 2 |
| `cache_meta.json` | 缓存元数据 | 2 |
| `usage_stats.json` | 资源使用统计（模拟） | 3 |
| `api_call_log.json` | API调用日志（真实计数） | 4 |
| `pending_questions.json` | 待办问题列表 | 2 |

## 版本历史

| 版本 | 日期 | 变更 |
|:---|:---|:---|
| v1.0 | 2026-06-21 | 初始版本（系统思维执行优化） |
| v2.0 | 2026-06-22 | 引入多尺度循环验证（基于Manifold Navigation Protocol裁剪） |
| v2.1 | 2026-06-22 | Phase 2：假设管理+问题铸造+缓存优化 |
| v3.0 | 2026-06-22 | Phase 3：势函数+流形距离+自适应执行层 |
| v2.0 | 2026-06-22 | 引入多尺度循环验证（基于Manifold Navigation Protocol裁剪） |
