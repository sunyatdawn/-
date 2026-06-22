#!/usr/bin/env python3
"""
Adaptive Executor - 自适应执行层
整合势函数和流形距离，动态调整扫描深度

核心理念：资源状态 + 关注域偏离度 → 决定执行策略
"""

import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from potential_function import PotentialFunction
from manifold_distance import ManifoldDistance

class AdaptiveExecutor:
    """
    自适应执行层
    
    输入：用户消息
    输出：执行策略（包含是否搜索、扫描深度、最大资源投入等）
    
    决策矩阵：
              | 资源充裕(>60%) | 资源中等(30-60%) | 资源紧张(<30%)
    ──────────┼─────────────────┼──────────────────┼────────────────
    核心(0-0.3)| 完整扫描+深度   | 标准扫描+精简     | 缓存+极简
    相关(0.3-0.6)| 标准扫描+深度 | 精简扫描+精简   | 缓存+极简
    边缘(0.6-0.9)| 精简扫描      | 极简处理         | 记录归档
    偏离(0.9-1.0)| 极简处理      | 记录归档         | 不处理/推迟
    """
    
    def __init__(self, workspace: str = "/root/.openclaw/workspace"):
        self.workspace = Path(workspace)
        self.pf = PotentialFunction(workspace)
        self.md = ManifoldDistance(workspace)
        
        self.decision_matrix = {
            ("core", "full"): {
                "scan_depth": "complete",
                "search_allowed": True,
                "max_search": 5,
                "analysis_depth": "deep",
                "use_cache": False
            },
            ("core", "reduced"): {
                "scan_depth": "essential",
                "search_allowed": True,
                "max_search": 2,
                "analysis_depth": "standard",
                "use_cache": True
            },
            ("core", "emergency"): {
                "scan_depth": "minimal",
                "search_allowed": False,
                "max_search": 0,
                "analysis_depth": "brief",
                "use_cache": True
            },
            ("related", "full"): {
                "scan_depth": "standard",
                "search_allowed": True,
                "max_search": 3,
                "analysis_depth": "standard",
                "use_cache": False
            },
            ("related", "reduced"): {
                "scan_depth": "minimal",
                "search_allowed": True,
                "max_search": 1,
                "analysis_depth": "brief",
                "use_cache": True
            },
            ("related", "emergency"): {
                "scan_depth": "minimal",
                "search_allowed": False,
                "max_search": 0,
                "analysis_depth": "brief",
                "use_cache": True
            },
            ("peripheral", "full"): {
                "scan_depth": "minimal",
                "search_allowed": True,
                "max_search": 1,
                "analysis_depth": "brief",
                "use_cache": True
            },
            ("peripheral", "reduced"): {
                "scan_depth": "minimal",
                "search_allowed": False,
                "max_search": 0,
                "analysis_depth": "minimal",
                "use_cache": True
            },
            ("peripheral", "emergency"): {
                "scan_depth": "none",
                "search_allowed": False,
                "max_search": 0,
                "analysis_depth": "none",
                "use_cache": True
            },
            ("deviated", "full"): {
                "scan_depth": "minimal",
                "search_allowed": False,
                "max_search": 0,
                "analysis_depth": "minimal",
                "use_cache": True
            },
            ("deviated", "reduced"): {
                "scan_depth": "none",
                "search_allowed": False,
                "max_search": 0,
                "analysis_depth": "none",
                "use_cache": True
            },
            ("deviated", "emergency"): {
                "scan_depth": "none",
                "search_allowed": False,
                "max_search": 0,
                "analysis_depth": "none",
                "use_cache": True
            }
        }
    
    def execute(self, user_input: str) -> Dict:
        """
        执行自适应决策
        
        流程：
        1. 检查是否为操作指令/状态查询（直通）
        2. 检查势函数（资源状态）
        3. 计算流形距离（偏离度）
        4. 查决策矩阵
        5. 输出执行策略
        
        Returns:
            执行策略
        """
        start_time = time.time()
        
        # 0. 检查是否为操作指令或状态查询 → 直通
        input_type = self._detect_input_type(user_input)
        if input_type in ("operation_command", "status_query"):
            return self._direct_pass_strategy(user_input, input_type, start_time)
        
        # 1. 检查资源状态
        resources = self.pf.check_resources()
        convergence = resources["convergence_level"]
        
        # 2. 计算流形距离
        distance = self.md.calculate_distance(user_input)
        dist_level = distance["distance_level"]
        
        # 3. 查决策矩阵
        strategy = self.decision_matrix.get(
            (dist_level, convergence),
            self._default_strategy()
        )
        
        # 4. 构建执行策略
        execution_plan = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "resource_status": {
                "score": resources["overall_score"],
                "convergence": convergence
            },
            "manifold_distance": {
                "distance": distance["overall_distance"],
                "level": dist_level,
                "matches": distance["matching_items"]
            },
            "strategy": strategy,
            "execution_steps": self._build_steps(strategy, user_input),
            "estimated_time_ms": 0,
            "confidence": self._calculate_confidence(resources, distance)
        }
        
        execution_plan["estimated_time_ms"] = int((time.time() - start_time) * 1000)
        
        return execution_plan
    
    def _build_steps(self, strategy: Dict, user_input: str) -> List[str]:
        """构建执行步骤"""
        steps = []
        
        # 第一步：全局扫描（总是执行，但深度不同）
        if strategy["scan_depth"] == "none":
            steps.append("[SKIP] 全局扫描（偏离关注域，跳过）")
        elif strategy["scan_depth"] == "minimal":
            steps.append("[MINIMAL] 全局扫描（仅读取缓存，不执行新扫描）")
        elif strategy["scan_depth"] == "essential":
            steps.append("[ESSENTIAL] 全局扫描（核心项）")
        else:
            steps.append("[COMPLETE] 全局扫描（完整三层）")
        
        # 第二步：搜索决策
        if strategy["search_allowed"]:
            steps.append(f"[SEARCH] 允许搜索（最多{strategy['max_search']}次）")
        else:
            steps.append("[SKIP] 搜索（资源紧张或偏离关注域）")
        
        # 第三步：分析深度
        depth_map = {
            "none": "[SKIP] 分析（跳过）",
            "minimal": "[MINIMAL] 分析（一句话回答）",
            "brief": "[BRIEF] 分析（简短回答，3-5点）",
            "standard": "[STANDARD] 分析（标准深度，要点完整）",
            "deep": "[DEEP] 分析（深度分析，详细论证）"
        }
        steps.append(depth_map.get(strategy["analysis_depth"], "[STANDARD] 分析"))
        
        return steps
    
    def _calculate_confidence(self, resources: Dict, distance: Dict) -> float:
        """计算策略置信度"""
        # 资源越充裕 + 距离越近 = 置信度越高
        resource_score = resources["overall_score"] / 100
        distance_score = 1 - distance["overall_distance"]
        
        confidence = (resource_score * 0.6 + distance_score * 0.4) * 100
        return round(confidence, 1)
    
    def _detect_input_type(self, text: str) -> str:
        """快速检测输入类型（不调用完整意图路由）"""
        text_lower = text.lower().strip()
        
        # 先检查是否包含股票名称/代码 → 不是操作指令/状态查询
        # 加载名称映射检查
        name_map = self.md.stock_name_map if hasattr(self, 'md') else {}
        for code, names in name_map.items():
            if code in text:
                return "analysis_request"
            for name in names:
                if name in text:
                    return "analysis_request"
        
        # 操作指令关键词（强特征，必须在句首或独立出现）
        operation_patterns = [
            r"^修复", r"^运行", r"^执行", r"^启动", r"^停止", r"^重启",
            r"^更新", r"^删除", r"^清除", r"^清理", r"^重新运行", r"^再跑一次",
            r"^fix\s", r"^run\s", r"^execute\s", r"^start\s", r"^stop\s",
        ]
        
        for pattern in operation_patterns:
            if re.search(pattern, text_lower):
                return "operation_command"
        
        # 状态查询关键词（强特征，必须在句首或作为核心词）
        status_patterns = [
            r"^状态", r"^进度", r"^情况", r"^现在什么",
            r"^status\s", r"^progress\s", r"^state\s",
            r"完成了吗", r"好了吗", r"结束了吗", r"跑完了吗",
            r"什么状态$", r"当前状态$", r"运行状态$",
        ]
        
        for pattern in status_patterns:
            if re.search(pattern, text_lower):
                return "status_query"
        
        return "analysis_request"  # 默认
    
    def _direct_pass_strategy(self, user_input: str, input_type: str, start_time: float) -> Dict:
        """操作指令/状态查询的直通策略（不评估距离）"""
        # 检查资源（即使是直通，也要确保资源不过度消耗）
        resources = self.pf.check_resources()
        
        # 操作指令 → 直接执行，不搜索
        if input_type == "operation_command":
            strategy = {
                "scan_depth": "minimal",
                "search_allowed": False,
                "max_search": 0,
                "analysis_depth": "minimal",
                "use_cache": True
            }
            reason = "操作指令直通"
        else:
            # 状态查询 → 查缓存，不搜索
            strategy = {
                "scan_depth": "minimal",
                "search_allowed": False,
                "max_search": 0,
                "analysis_depth": "brief",
                "use_cache": True
            }
            reason = "状态查询直通"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "input_type": input_type,
            "resource_status": {
                "score": resources["overall_score"],
                "convergence": resources["convergence_level"]
            },
            "manifold_distance": {
                "distance": 0.0,
                "level": "core",  # 标记为core，表示不评估距离
                "matches": [reason]
            },
            "strategy": strategy,
            "execution_steps": [
                f"[DIRECT] {reason}，跳过流形距离评估",
                f"[EXECUTE] 直接执行：{user_input}",
                "[SKIP] 搜索（操作指令不需要搜索）"
            ],
            "estimated_time_ms": int((time.time() - start_time) * 1000),
            "confidence": 95.0,
            "direct_pass": True
        }
    
    def _default_strategy(self) -> Dict:
        """默认策略"""
        return {
            "scan_depth": "essential",
            "search_allowed": True,
            "max_search": 2,
            "analysis_depth": "standard",
            "use_cache": True
        }
    
    def get_execution_summary(self, plan: Dict) -> str:
        """获取执行策略摘要（用于回复标记）"""
        resource = plan["resource_status"]
        distance = plan["manifold_distance"]
        strategy = plan["strategy"]
        
        return (
            f"[自适应执行] "
            f"资源={resource['convergence']}({resource['score']}) | "
            f"距离={distance['level']}({distance['distance']}) | "
            f"搜索={'是' if strategy['search_allowed'] else '否'} | "
            f"深度={strategy['analysis_depth']}"
        )


def main():
    import sys
    
    executor = AdaptiveExecutor()
    
    if len(sys.argv) > 1:
        user_input = sys.argv[1]
        plan = executor.execute(user_input)
        
        print("=" * 60)
        print("🎯 自适应执行策略")
        print("=" * 60)
        print(f"输入: {plan['user_input']}")
        print()
        print(f"资源状态: {plan['resource_status']['convergence']} "
              f"(分数: {plan['resource_status']['score']})")
        print(f"流形距离: {plan['manifold_distance']['level']} "
              f"({plan['manifold_distance']['distance']})")
        print(f"匹配项: {plan['manifold_distance']['matches']}")
        print()
        print("执行策略:")
        print(f"  搜索: {'允许' if plan['strategy']['search_allowed'] else '禁止'} "
              f"(最多{plan['strategy']['max_search']}次)")
        print(f"  扫描深度: {plan['strategy']['scan_depth']}")
        print(f"  分析深度: {plan['strategy']['analysis_depth']}")
        print(f"  使用缓存: {'是' if plan['strategy']['use_cache'] else '否'}")
        print()
        print("执行步骤:")
        for i, step in enumerate(plan['execution_steps'], 1):
            print(f"  {i}. {step}")
        print()
        print(f"置信度: {plan['confidence']}%")
        print(f"策略耗时: {plan['estimated_time_ms']}ms")
        print("=" * 60)
        
    else:
        # 测试
        test_inputs = [
            "沪硅产业现在怎么样？",
            "MLCC产业链分析",
            "今天天气怎么样？",
            "修复同步问题",
        ]
        
        print("=" * 60)
        print("🎯 自适应执行测试")
        print("=" * 60)
        
        for inp in test_inputs:
            plan = executor.execute(inp)
            summary = executor.get_execution_summary(plan)
            is_direct = plan.get("direct_pass", False)
            print(f"\n输入: {inp}")
            print(f"  {summary}")
            if is_direct:
                print(f"  [直通] 类型={plan['input_type']}, 原因={plan['manifold_distance']['matches'][0]}")
        
        print("=" * 60)


if __name__ == "__main__":
    main()
