#!/usr/bin/env python3
"""
Potential Function - 势函数预警系统
监控资源状态，接近阈值时触发思维收敛

核心理念：资源是有限的"势能"，当接近耗尽时必须收敛
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class PotentialFunction:
    """
    势函数预警系统
    
    监控维度：
    - API调用次数（搜索/分析等）
    - 上下文token长度
    - 任务执行时间
    - 扫描器响应时间
    
    收敛策略：
    - 资源充裕 (>60%)：完整执行
    - 资源中等 (30-60%)：精简模式
    - 资源紧张 (<30%)：紧急收敛
    """
    
    def __init__(self, workspace: str = "/root/.openclaw/workspace"):
        self.workspace = Path(workspace)
        self.usage_file = self.workspace / "skills" / "daguan" / "usage_stats.json"
        
        # 配置阈值（可根据实际环境调整）
        self.thresholds = {
            "api_calls": {"daily_limit": 100, "warning": 70, "critical": 90},
            "context_tokens": {"limit": 8000, "warning": 5600, "critical": 7200},
            "task_timeout": {"limit": 300, "warning": 180, "critical": 240},  # 秒
            "scanner_time": {"limit": 5, "warning": 3, "critical": 4}  # 秒
        }
    
    # ═══════════════════════════════════════════════════════
    # 资源监控
    # ═══════════════════════════════════════════════════════
    def check_resources(self) -> Dict:
        """
        检查当前资源状态
        
        Returns:
            资源状态报告
        """
        resources = {
            "timestamp": datetime.now().isoformat(),
            "api_calls": self._check_api_usage(),
            "context_length": self._check_context_length(),
            "time_budget": self._check_time_budget(),
            "scanner_latency": self._check_scanner_latency()
        }
        
        # 计算综合资源分数 (0-100)
        resources["overall_score"] = self._calculate_overall_score(resources)
        
        # 确定收敛策略
        resources["convergence_level"] = self._determine_convergence(
            resources["overall_score"]
        )
        
        # 生成建议
        resources["recommendations"] = self._generate_recommendations(resources)
        
        return resources
    
    def _check_api_usage(self) -> Dict:
        """检查API调用次数（对接真实计数器）"""
        # 从 api_counter 读取真实计数
        try:
            from api_counter import get_today_usage
            usage = get_today_usage()
            
            today_calls = usage["total_used"]
            limit = usage["total_limit"]
            
            # 计算各分类中最紧张的
            max_ratio = 0
            tightest_category = ""
            for cat, data in usage["by_category"].items():
                if data["ratio"] > max_ratio:
                    max_ratio = data["ratio"]
                    tightest_category = cat
            
            percentage = max_ratio * 100
            
            return {
                "today_calls": today_calls,
                "daily_limit": limit,
                "percentage": round(percentage, 1),
                "status": usage["overall_status"],
                "remaining": usage["total_remaining"],
                "tightest_category": tightest_category,
                "category_detail": usage["by_category"]
            }
        except Exception as e:
            # 回退到旧方法
            usage = self._load_usage_stats()
            today = datetime.now().strftime("%Y-%m-%d")
            today_calls = usage.get("daily_calls", {}).get(today, 0)
            
            limit = self.thresholds["api_calls"]["daily_limit"]
            warning = self.thresholds["api_calls"]["warning"]
            critical = self.thresholds["api_calls"]["critical"]
            
            percentage = (today_calls / limit) * 100 if limit > 0 else 0
            
            return {
                "today_calls": today_calls,
                "daily_limit": limit,
                "percentage": round(percentage, 1),
                "status": self._status_label(percentage, warning, critical),
                "remaining": limit - today_calls,
                "fallback": True,
                "error": str(e)
            }
    
    def _check_context_length(self) -> Dict:
        """检查上下文长度（估算）"""
        # 简单估算：读取最近的memory文件大小
        memory_dir = self.workspace / "memory"
        total_size = 0
        
        if memory_dir.exists():
            for f in memory_dir.glob("*.json"):
                total_size += f.stat().st_size
        
        # 粗略估算：1KB ≈ 250 tokens
        estimated_tokens = total_size / 4
        
        limit = self.thresholds["context_tokens"]["limit"]
        warning = self.thresholds["context_tokens"]["warning"]
        critical = self.thresholds["context_tokens"]["critical"]
        
        percentage = (estimated_tokens / limit) * 100 if limit > 0 else 0
        
        return {
            "estimated_tokens": int(estimated_tokens),
            "limit": limit,
            "percentage": round(percentage, 1),
            "status": self._status_label(percentage, warning, critical)
        }
    
    def _check_time_budget(self) -> Dict:
        """检查时间预算"""
        # 读取当前会话开始时间
        usage = self._load_usage_stats()
        session_start = usage.get("session_start")
        
        if session_start:
            elapsed = (datetime.now() - datetime.fromisoformat(session_start)).total_seconds()
        else:
            elapsed = 0
        
        limit = self.thresholds["task_timeout"]["limit"]
        warning = self.thresholds["task_timeout"]["warning"]
        critical = self.thresholds["task_timeout"]["critical"]
        
        percentage = (elapsed / limit) * 100 if limit > 0 else 0
        
        return {
            "elapsed_seconds": int(elapsed),
            "limit": limit,
            "percentage": round(percentage, 1),
            "status": self._status_label(percentage, warning, critical),
            "remaining": int(limit - elapsed)
        }
    
    def _check_scanner_latency(self) -> Dict:
        """检查扫描器延迟"""
        usage = self._load_usage_stats()
        last_scan_time = usage.get("last_scan_time_ms", 0)
        
        limit = self.thresholds["scanner_time"]["limit"]
        warning = self.thresholds["scanner_time"]["warning"]
        critical = self.thresholds["scanner_time"]["critical"]
        
        percentage = (last_scan_time / (limit * 1000)) * 100 if limit > 0 else 0
        
        return {
            "last_scan_ms": last_scan_time,
            "limit_ms": limit * 1000,
            "percentage": round(percentage, 1),
            "status": self._status_label(percentage, warning, critical)
        }
    
    # ═══════════════════════════════════════════════════════
    # 综合评估
    # ═══════════════════════════════════════════════════════
    def _calculate_overall_score(self, resources: Dict) -> float:
        """计算综合资源分数 (0-100)"""
        scores = [
            100 - resources["api_calls"]["percentage"],
            100 - resources["context_length"]["percentage"],
            100 - resources["time_budget"]["percentage"],
            100 - resources["scanner_latency"]["percentage"]
        ]
        
        # 取最差维度（木桶理论）
        return round(min(scores), 1)
    
    def _determine_convergence(self, overall_score: float) -> str:
        """确定收敛级别"""
        if overall_score > 60:
            return "full"  # 完整执行
        elif overall_score > 30:
            return "reduced"  # 精简模式
        else:
            return "emergency"  # 紧急收敛
    
    def _generate_recommendations(self, resources: Dict) -> List[str]:
        """生成收敛建议"""
        recommendations = []
        level = resources["convergence_level"]
        
        if level == "full":
            recommendations.append("资源充裕，可执行完整扫描和分析")
        elif level == "reduced":
            recommendations.append("⚠️ 资源中等，建议精简模式：")
            recommendations.append("  - 跳过非核心检查项")
            recommendations.append("  - 减少搜索次数（最多2次）")
            recommendations.append("  - 缩短分析深度")
        elif level == "emergency":
            recommendations.append("🚨 资源紧张，紧急收敛：")
            recommendations.append("  - 只保留最高优先级任务")
            recommendations.append("  - 跳过搜索，直接查文档/memory")
            recommendations.append("  - 使用缓存数据，不执行新扫描")
        
        # 具体维度建议
        if resources["api_calls"]["status"] == "critical":
            recommendations.append("🚫 API调用接近上限，禁止新搜索")
        if resources["context_length"]["status"] == "critical":
            recommendations.append("🚫 上下文接近压缩阈值，建议总结历史")
        
        return recommendations
    
    def _status_label(self, percentage: float, warning: float, critical: float) -> str:
        """根据百分比返回状态标签"""
        if percentage >= critical:
            return "critical"
        elif percentage >= warning:
            return "warning"
        else:
            return "normal"
    
    # ═══════════════════════════════════════════════════════
    # 使用统计管理
    # ═══════════════════════════════════════════════════════
    def _load_usage_stats(self) -> Dict:
        """加载使用统计"""
        if self.usage_file.exists():
            with open(self.usage_file, 'r') as f:
                return json.load(f)
        return {
            "daily_calls": {},
            "session_start": datetime.now().isoformat(),
            "last_scan_time_ms": 0
        }
    
    def record_api_call(self, call_type: str = "search"):
        """记录一次API调用"""
        stats = self._load_usage_stats()
        today = datetime.now().strftime("%Y-%m-%d")
        
        if today not in stats["daily_calls"]:
            stats["daily_calls"][today] = 0
        stats["daily_calls"][today] += 1
        
        with open(self.usage_file, 'w') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    
    def record_scan_time(self, elapsed_ms: int):
        """记录扫描器执行时间"""
        stats = self._load_usage_stats()
        stats["last_scan_time_ms"] = elapsed_ms
        
        with open(self.usage_file, 'w') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    
    # ═══════════════════════════════════════════════════════
    # 收敛策略应用
    # ═══════════════════════════════════════════════════════
    def apply_convergence(self, original_plan: Dict) -> Dict:
        """
        根据资源状态调整执行计划
        
        Args:
            original_plan: 原始执行计划
        
        Returns:
            调整后的执行计划
        """
        resources = self.check_resources()
        level = resources["convergence_level"]
        
        adjusted = original_plan.copy()
        
        if level == "full":
            # 完整执行，无需调整
            adjusted["execution_mode"] = "full"
            adjusted["search_allowed"] = True
            adjusted["max_search_count"] = 5
            adjusted["scan_depth"] = "complete"
            
        elif level == "reduced":
            # 精简模式
            adjusted["execution_mode"] = "reduced"
            adjusted["search_allowed"] = True
            adjusted["max_search_count"] = 2
            adjusted["scan_depth"] = "essential"
            # 跳过非核心检查项
            adjusted["skip_items"] = ["微观细节", "历史追溯", "跨链验证"]
            
        elif level == "emergency":
            # 紧急收敛
            adjusted["execution_mode"] = "emergency"
            adjusted["search_allowed"] = False
            adjusted["max_search_count"] = 0
            adjusted["scan_depth"] = "minimal"
            # 只保留最高优先级
            adjusted["skip_items"] = ["搜索", "深度分析", "多源验证", "跨链验证"]
            adjusted["use_cache_only"] = True
        
        adjusted["resource_status"] = resources
        
        return adjusted


def main():
    import sys
    
    pf = PotentialFunction()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        resources = pf.check_resources()
        print("=" * 60)
        print("📊 势函数预警报告")
        print("=" * 60)
        print(f"综合资源分数: {resources['overall_score']}/100")
        print(f"收敛级别: {resources['convergence_level']}")
        print()
        print("各维度状态:")
        print(f"  API调用: {resources['api_calls']['today_calls']}/{resources['api_calls']['daily_limit']} ({resources['api_calls']['status']})")
        print(f"  上下文: {resources['context_length']['estimated_tokens']} tokens ({resources['context_length']['status']})")
        print(f"  时间预算: {resources['time_budget']['elapsed_seconds']}s/{resources['time_budget']['limit']}s ({resources['time_budget']['status']})")
        print(f"  扫描延迟: {resources['scanner_latency']['last_scan_ms']}ms ({resources['scanner_latency']['status']})")
        print()
        print("建议:")
        for rec in resources['recommendations']:
            print(f"  {rec}")
        print("=" * 60)
        
    elif len(sys.argv) > 1 and sys.argv[1] == "--record-call":
        pf.record_api_call()
        print("✅ API调用已记录")
        
    else:
        print("Usage:")
        print("  python3 potential_function.py --check        # 检查资源状态")
        print("  python3 potential_function.py --record-call    # 记录API调用")


if __name__ == "__main__":
    main()
