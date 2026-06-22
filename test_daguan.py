#!/usr/bin/env python3
"""
大观（Daguan）技能综合测试套件
测试L1-L4全部组件
"""

import json
import sys
from pathlib import Path

# 添加技能路径
sys.path.insert(0, "/root/.openclaw/workspace/skills/daguan")

from multi_scale_scanner import MultiScaleScanner
from hypothesis_manager import HypothesisManager
from potential_function import PotentialFunction
from manifold_distance import ManifoldDistance
from adaptive_executor import AdaptiveExecutor
from api_counter import APICounter, count_tool_call, get_today_usage

class DaguanTestSuite:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def test(self, name, condition, details=""):
        """运行单个测试"""
        if condition:
            self.passed += 1
            status = "✅ PASS"
        else:
            self.failed += 1
            status = "❌ FAIL"
        
        self.tests.append({
            "name": name,
            "status": status,
            "details": details
        })
        
        print(f"  {status} {name}")
        if details and not condition:
            print(f"      → {details}")
    
    def run_all(self):
        """运行全部测试"""
        print("=" * 70)
        print("🧪 大观（Daguan）技能综合测试套件")
        print("=" * 70)
        
        # ═══════════════════════════════════════════════════════
        # L1: 多尺度扫描器
        # ═══════════════════════════════════════════════════════
        print("\n📊 Layer 1: 多尺度扫描器")
        print("-" * 50)
        
        scanner = MultiScaleScanner()
        
        # 测试1: 状态查询识别
        result = scanner.full_scan("修复同步问题")
        self.test(
            "状态查询识别",
            result["micro"]["input_type"] == "operation_command",
            f"期望 operation_command，实际 {result['micro']['input_type']}"
        )
        
        # 测试2: 分析请求识别
        result = scanner.full_scan("沪硅产业现在怎么样？")
        self.test(
            "分析请求识别",
            result["micro"]["input_type"] == "analysis_request",
            f"期望 analysis_request，实际 {result['micro']['input_type']}"
        )
        
        # 测试3: 一般聊天识别（天气查询应识别为general_chat）
        result = scanner.full_scan("今天天气怎么样？")
        self.test(
            "一般聊天识别",
            result["micro"]["input_type"] == "general_chat",
            f"实际 {result['micro']['input_type']}（应识别为general_chat）"
        )
        
        # 测试3b: 问候语识别
        result = scanner.full_scan("你好")
        self.test(
            "问候语识别",
            result["micro"]["input_type"] == "general_chat",
            f"实际 {result['micro']['input_type']}"
        )
        
        # 测试4: 关注池代码匹配（688126在关注池中）
        result = scanner.full_scan("688126")
        self.test(
            "关注池代码匹配",
            result["micro"]["related_to_watch_pool"] == True,
            f"688126 应匹配关注池，实际 related_to_watch_pool={result['micro']['related_to_watch_pool']}"
        )
        
        # 测试5: 风险等级评估
        result = scanner.full_scan("紧急！系统崩溃了！")
        self.test(
            "紧急输入识别",
            result["micro"]["urgency"] == "urgent",
            f"期望 urgent，实际 {result['micro']['urgency']}"
        )
        
        # ═══════════════════════════════════════════════════════
        # L2: 假设管理
        # ═══════════════════════════════════════════════════════
        print("\n🧠 Layer 2: 假设管理")
        print("-" * 50)
        
        hm = HypothesisManager()
        
        # 测试6: 创建假设
        hypo_id = hm.track_assumption(
            "MLCC价格将在Q3上涨",
            "user"
        )
        self.test(
            "创建假设",
            hypo_id is not None,
            "假设创建失败"
        )
        
        # 测试7: 检查锚点
        result = hm.check_anchor("MLCC价格上涨", ["report_001", "user_input"])
        self.test(
            "锚点检查",
            result["anchor_strength"] == "strong",
            f"期望 strong，实际 {result['anchor_strength']}"
        )
        
        # 测试8: 验证假设
        validated = hm.verify_assumption(hypo_id, "confirmed")
        self.test(
            "验证假设",
            validated == True,
            "假设验证失败"
        )
        
        # 测试9: 待验证假设列表
        pending = hm.get_pending_verifications()
        self.test(
            "待验证假设列表",
            isinstance(pending, list),
            "应返回列表"
        )
        
        # 测试9b: 最近假设（跨会话加载）
        recent = hm.get_recent_hypotheses(days=7)
        self.test(
            "最近假设获取",
            isinstance(recent, list) and len(recent) > 0,
            f"应返回最近假设，实际 {len(recent)} 条"
        )
        
        # 测试9c: 会话摘要生成
        summary = hm.load_recent_for_session(days=7)
        self.test(
            "假设摘要生成",
            "大观·活跃假设" in summary or summary == "",
            f"摘要格式异常"
        )
        
        # ═══════════════════════════════════════════════════════
        # L3: 势函数
        # ═══════════════════════════════════════════════════════
        print("\n⚡ Layer 3: 势函数预警")
        print("-" * 50)
        
        pf = PotentialFunction()
        
        # 测试10: 资源检查
        resources = pf.check_resources()
        self.test(
            "资源检查运行",
            "overall_score" in resources,
            "资源检查未返回总分"
        )
        
        # 测试11: API使用检查
        api_status = resources.get("api_calls", {})
        self.test(
            "API状态检查",
            "status" in api_status or "today_calls" in api_status,
            f"API状态键: {list(api_status.keys())}"
        )
        
        # 测试12: 收敛级别
        convergence = resources.get("convergence_level", "")
        self.test(
            "收敛级别有效",
            convergence in ["full", "moderate", "critical"],
            f"收敛级别 {convergence} 无效"
        )
        
        # 测试13: 建议存在
        recommendations = resources.get("recommendations", [])
        self.test(
            "建议生成",
            len(recommendations) > 0,
            "建议为空"
        )
        
        # ═══════════════════════════════════════════════════════
        # L3: 流形距离
        # ═══════════════════════════════════════════════════════
        print("\n📐 Layer 3: 流形距离评估")
        print("-" * 50)
        
        md = ManifoldDistance()
        
        # 测试14: 核心持仓命中
        result = md.calculate_distance("沪硅产业现在怎么样？")
        self.test(
            "核心持仓距离",
            result["distance_level"] == "core" and result["overall_distance"] < 0.3,
            f"距离={result['overall_distance']}, 等级={result['distance_level']}"
        )
        
        # 测试15: 名称映射
        result = md.calculate_distance("北方铜业怎么看？")
        self.test(
            "名称映射识别",
            result["distance_level"] == "core",
            f"北方铜业应识别为core，实际 {result['distance_level']}"
        )
        
        # 测试16: 偏离输入
        result = md.calculate_distance("今天天气怎么样？")
        self.test(
            "偏离输入识别",
            result["distance_level"] == "deviated",
            f"天气应识别为deviated，实际 {result['distance_level']}"
        )
        
        # 测试17: 兴趣行业
        result = md.calculate_distance("MLCC产业链分析")
        self.test(
            "兴趣行业匹配",
            result["distance_level"] in ["related", "peripheral"],
            f"MLCC应匹配兴趣行业，实际 {result['distance_level']}"
        )
        
        # ═══════════════════════════════════════════════════════
        # L4: 自适应执行层
        # ═══════════════════════════════════════════════════════
        print("\n🎯 Layer 4: 自适应执行层")
        print("-" * 50)
        
        executor = AdaptiveExecutor()
        
        # 测试18: 核心输入策略
        plan = executor.execute("沪硅产业现在怎么样？")
        self.test(
            "核心输入策略",
            plan["strategy"]["search_allowed"] == True and plan["strategy"]["analysis_depth"] == "deep",
            f"搜索={plan['strategy']['search_allowed']}, 深度={plan['strategy']['analysis_depth']}"
        )
        
        # 测试19: 偏离输入策略
        plan = executor.execute("今天天气怎么样？")
        self.test(
            "偏离输入策略",
            plan["strategy"]["search_allowed"] == False and plan["strategy"]["analysis_depth"] == "minimal",
            f"搜索={plan['strategy']['search_allowed']}, 深度={plan['strategy']['analysis_depth']}"
        )
        
        # 测试20: 操作指令直通
        plan = executor.execute("修复同步问题")
        self.test(
            "操作指令直通",
            plan.get("direct_pass") == True,
            "操作指令应触发直通"
        )
        
        # 测试21: 状态查询直通
        plan = executor.execute("现在什么情况？")
        self.test(
            "状态查询直通",
            plan.get("direct_pass") == True,
            "状态查询应触发直通"
        )
        
        # 测试22: 策略包含标记
        summary = executor.get_execution_summary(plan)
        self.test(
            "策略摘要生成",
            len(summary) > 0,
            "策略摘要为空"
        )
        
        # ═══════════════════════════════════════════════════════
        # L4: API计数器
        # ═══════════════════════════════════════════════════════
        print("\n🔢 Layer 4: API计数器")
        print("-" * 50)
        
        counter = APICounter()
        
        # 测试23: 计数功能
        result = counter.count("kimi_search", "测试计数")
        self.test(
            "计数功能",
            result["category"] == "search",
            f"期望 search，实际 {result['category']}"
        )
        
        # 测试24: 用量查询
        usage = counter.get_today_usage()
        self.test(
            "用量查询",
            "total_used" in usage and "total_limit" in usage,
            "用量查询结构不完整"
        )
        
        # 测试25: 便捷函数
        count_tool_call("kimi_finance", "测试价格查询")
        usage = get_today_usage()
        self.test(
            "便捷函数",
            usage["total_used"] > 0,
            "便捷函数未计数"
        )
        
        # 测试26: 状态判断
        self.test(
            "状态正常",
            usage["overall_status"] == "NORMAL",
            f"状态={usage['overall_status']}"
        )
        
        # ═══════════════════════════════════════════════════════
        # 端到端测试
        # ═══════════════════════════════════════════════════════
        print("\n🔁 端到端测试")
        print("-" * 50)
        
        # 测试27: 完整流程 - 分析请求
        user_input = "分析一下MLCC产业链"
        
        # L1
        scan = scanner.full_scan(user_input)
        # L3 - 势函数
        resources = pf.check_resources()
        # L3 - 流形距离
        distance = md.calculate_distance(user_input)
        # L4 - 自适应执行
        plan = executor.execute(user_input)
        
        self.test(
            "端到端-分析请求",
            scan["micro"]["input_type"] == "analysis_request" 
            and plan["strategy"]["search_allowed"] == True,
            f"类型={scan['micro']['input_type']}, 搜索={plan['strategy']['search_allowed']}"
        )
        
        # 测试28: 完整流程 - 操作指令
        user_input = "修复bug"
        scan = scanner.full_scan(user_input)
        plan = executor.execute(user_input)
        
        self.test(
            "端到端-操作指令",
            scan["micro"]["input_type"] == "operation_command"
            and plan.get("direct_pass") == True,
            f"类型={scan['micro']['input_type']}, 直通={plan.get('direct_pass')}"
        )
        
        # ═══════════════════════════════════════════════════════
        # 测试总结
        # ═══════════════════════════════════════════════════════
        print("\n" + "=" * 70)
        print("📊 测试结果汇总")
        print("=" * 70)
        print(f"\n✅ 通过: {self.passed}")
        print(f"❌ 失败: {self.failed}")
        print(f"📈 总计: {self.passed + self.failed}")
        print(f"🎯 通过率: {self.passed/(self.passed + self.failed)*100:.1f}%")
        
        if self.failed > 0:
            print("\n❌ 失败项详情:")
            for test in self.tests:
                if test["status"].startswith("❌"):
                    print(f"  - {test['name']}: {test['details']}")
        
        print("\n" + "=" * 70)
        
        return self.failed == 0


if __name__ == "__main__":
    suite = DaguanTestSuite()
    success = suite.run_all()
    sys.exit(0 if success else 1)
