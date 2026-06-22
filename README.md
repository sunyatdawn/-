# Daguan（大观）- 全局思维系统

> **多尺度循环验证引擎，让 AI Agent 先见森林再见树木。**

[![Version](https://img.shields.io/badge/version-3.0.0-blue)](https://github.com)
[![Python](https://img.shields.io/badge/python-3.10+-green)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

## 什么是大观？

**大观**（Daguan）是一个为 AI Agent 设计的**全局思维系统**。它强制 Agent 在每次回复前执行三层扫描（宏观/中观/微观），确保决策基于全局上下文而非局部信息。

**核心原则**：先见森林，再见树木。延迟 2-3 秒，换取全局视角。

## 五层架构

```
用户输入
    ↓
【Layer 0】意图识别
    ↓
【Layer 1】多尺度全局扫描 ← 宏观/中观/微观
    ↓
【Layer 2】锚点+假设审查
    ↓
【Layer 3】势函数预警 + 流形距离评估
    ↓
【Layer 4】自适应执行层
    ↓
【Layer 5】问题铸造器
    ↓
组织答案
```

## 核心能力

| 能力 | 说明 | 对应文件 |
|:---|:---|:---|
| **多尺度扫描** | 宏观(市场)/中观(用户)/微观(输入) | `multi_scale_scanner.py` |
| **假设管理** | 创建/验证/回顾/过期管理 | `hypothesis_manager.py` |
| **势函数预警** | API计数/上下文长度/时间预算 | `potential_function.py` |
| **流形距离** | 量化输入与关注域的偏离度 | `manifold_distance.py` |
| **自适应执行** | 4×3 决策矩阵（距离×资源） | `adaptive_executor.py` |
| **API计数器** | 真实工具调用计数与限额 | `api_counter.py` |
| **问题铸造器** | 从残留异常生成新问题 | `question_foundry.py` |

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/yourname/daguan.git
cd daguan

# 2. 安装依赖（纯 Python 标准库，无额外依赖）
# 无需安装，直接运行

# 3. 测试
python3 test_daguan.py
# 预期: 31/31 通过

# 4. 使用
python3 multi_scale_scanner.py "你的输入"
```

## 使用示例

### 基础扫描
```python
from multi_scale_scanner import MultiScaleScanner

scanner = MultiScaleScanner()
result = scanner.full_scan("分析一下MLCC产业链")

print(result["micro"]["input_type"])      # analysis_request
print(result["global_assessment"]["relevance_level"])  # high
```

### 假设管理
```python
from hypothesis_manager import HypothesisManager

hm = HypothesisManager()

# 创建假设
hid = hm.track_assumption("MLCC价格Q3上涨", "user")

# 验证假设
hm.verify_assumption(hid, "industry_report_001")

# 跨会话加载
summary = hm.load_recent_for_session(days=7)
```

### 流形距离评估
```python
from manifold_distance import ManifoldDistance

md = ManifoldDistance()
result = md.calculate_distance("沪硅产业现在怎么样？")

print(result["distance_level"])      # core (0.0-0.3)
print(result["overall_distance"])    # 0.0
```

## 项目结构

```
daguan/
├── SKILL.md                    # 技能规范（五层架构、红线规则）
├── README.md                   # 本文件
├── LICENSE                     # MIT 许可证
│
├── multi_scale_scanner.py      # Layer 1: 多尺度扫描器
├── hypothesis_manager.py       # Layer 2: 假设管理
├── hypothesis_review.py        # Layer 2: 假设定期回顾
├── question_foundry.py         # Layer 5: 问题铸造器
│
├── potential_function.py       # Layer 3: 势函数预警
├── manifold_distance.py        # Layer 3: 流形距离评估
├── adaptive_executor.py        # Layer 4: 自适应执行层
├── api_counter.py              # Layer 4: API计数器
├── api_counter_config.json     # 计数器配置
│
├── global_state_cache.py       # 缓存更新器（15分钟cron）
├── test_daguan.py              # 综合测试套件（31/31通过）
│
├── stock_name_map.json         # 名称映射（32只股票）
├── recent_topics.json          # 近期话题（14个，48h TTL）
│
├── global_state.json           # 扫描结果缓存
├── hypotheses.json             # 假设数据库
├── cache_meta.json             # 缓存元数据
├── api_call_log.json           # API调用日志
└── usage_stats.json            # 资源使用统计
```

## 测试

```bash
python3 test_daguan.py
```

**预期输出**:
```
🧪 大观（Daguan）技能综合测试套件

📊 Layer 1: 多尺度扫描器
  ✅ PASS 状态查询识别
  ✅ PASS 分析请求识别
  ✅ PASS 一般聊天识别
  ✅ PASS 问候语识别
  ✅ PASS 关注池代码匹配
  ✅ PASS 紧急输入识别

🧠 Layer 2: 假设管理
  ✅ PASS 创建假设
  ✅ PASS 锚点检查
  ✅ PASS 验证假设
  ✅ PASS 待验证假设列表
  ✅ PASS 最近假设获取
  ✅ PASS 假设摘要生成

⚡ Layer 3: 势函数预警
  ✅ PASS 资源检查运行
  ✅ PASS API状态检查
  ✅ PASS 收敛级别有效
  ✅ PASS 建议生成

📐 Layer 3: 流形距离评估
  ✅ PASS 核心持仓距离
  ✅ PASS 名称映射识别
  ✅ PASS 偏离输入识别
  ✅ PASS 兴趣行业匹配

🎯 Layer 4: 自适应执行层
  ✅ PASS 核心输入策略
  ✅ PASS 偏离输入策略
  ✅ PASS 操作指令直通
  ✅ PASS 状态查询直通
  ✅ PASS 策略摘要生成

🔢 Layer 4: API计数器
  ✅ PASS 计数功能
  ✅ PASS 用量查询
  ✅ PASS 便捷函数
  ✅ PASS 状态正常

🔁 端到端测试
  ✅ PASS 端到端-分析请求
  ✅ PASS 端到端-操作指令

✅ 通过: 31 | ❌ 失败: 0 | 通过率: 100.0%
```

## 与现有技能的对接

| 技能 | 大观的作用 |
|:---|:---|
| 意图路由 | 在 Layer 0 后执行，提供全局上下文辅助意图判断 |
| PUA | 提供数据支撑（全局扫描结果），PUA 提供执行压力 |
| anysearch | 决定"是否搜索、搜索什么"，anysearch 执行搜索 |
| MEMORY.md | 读取 MEMORY 作为中观输入，同时更新假设和状态 |

## 输入类型决策

| input_type | 处理方式 | 是否搜索 |
|:---|:---|:---:|
| `status_query` | 查文档/memory，直接回答 | ❌ |
| `operation_command` | 直接执行，记录日志 | ❌ |
| `analysis_request` | 分析请求，检查关联度 | 看关联度 |
| `search_request` | 搜索请求，明确关键词 | ✅ |
| `general_chat` | 一般对话，判断是否需要搜索 | 看内容 |

## 资源限额

| 类别 | 工具 | 日限额 |
|:---|:---|:---:|
| search | kimi_search, kimi_fetch, web_fetch, browser | 80 |
| finance | kimi_finance, kimi_datasource_call | 30 |
| web | web_fetch, kimi_fetch | 20 |
| other | image, pdf, tts | 20 |

## 红线规则

🚫 **未执行全局扫描禁止回复**：没有 `[全局扫描完成]` 标记的回复视为不合格
🚫 **无条件搜索禁止**：未经扫描决策步骤，不得直接调用搜索工具
🚫 **逻辑漂移禁止**：结论与锚点事实矛盾时，必须优先质疑假设
🚫 **假设未标注禁止**：任何未验证的判断必须标注 `[ASSUMPTION:状态]`

## 版本历史

| 版本 | 日期 | 变更 |
|:---|:---|:---|
| v1.0 | 2026-06-21 | 初始版本（系统思维执行优化） |
| v2.0 | 2026-06-22 | 引入多尺度循环验证（Manifold Navigation Protocol） |
| v2.1 | 2026-06-22 | Phase 2：假设管理+问题铸造+缓存优化 |
| v3.0 | 2026-06-22 | Phase 3：势函数+流形距离+自适应执行层 |
| v3.1 | 2026-06-22 | Phase 4：API计数对接+名称映射+测试套件 |

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 致谢

基于 Manifold Navigation Protocol 裁剪实现，适配中文金融 AI Agent 场景。
