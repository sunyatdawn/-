#!/usr/bin/env python3
"""
API Counter - API调用计数器（方案A）
每次调用外部工具前执行计数，写入api_call_log.json
potential_function.py读取真实计数进行资源评估

使用方法:
    from api_counter import count_tool_call, get_today_usage
    
    # 调用工具前计数
    count_tool_call("kimi_search")
    
    # 查询今日用量
    usage = get_today_usage()
    print(f"今日已用: {usage['total']} / {usage['limit']}")
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

class APICounter:
    """
    API调用计数器
    
    分类计数：
    - search: kimi_search, kimi_fetch, web_fetch, browser
    - finance: kimi_finance, kimi_datasource_call
    - web: web_fetch, kimi_fetch
    - other: image, pdf, tts
    
    限制：
    - search: 80/天
    - finance: 30/天
    - web: 20/天
    - other: 20/天
    """
    
    def __init__(self, workspace: str = "/root/.openclaw/workspace"):
        self.workspace = Path(workspace)
        self.log_file = self.workspace / "skills" / "daguan" / "api_call_log.json"
        self.config_file = self.workspace / "skills" / "daguan" / "api_counter_config.json"
        
        self.config = self._load_config()
        self.log_data = self._load_log()
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if not self.config_file.exists():
            # 默认配置
            return {
                "daily_limits": {
                    "search": 80,
                    "finance": 30,
                    "web": 20,
                    "other": 20
                },
                "limit_definitions": {
                    "search": ["kimi_search", "kimi_fetch", "web_fetch", "browser"],
                    "finance": ["kimi_finance", "kimi_datasource_call"],
                    "web": ["web_fetch", "kimi_fetch"],
                    "other": ["image", "pdf", "tts"]
                },
                "warning_threshold": 0.8,
                "emergency_threshold": 0.95,
                "reset_hour": 0
            }
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_log(self) -> Dict:
        """加载日志"""
        if not self.log_file.exists():
            return {"version": "1.0.0", "daily_logs": {}}
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"version": "1.0.0", "daily_logs": {}}
    
    def _save_log(self):
        """保存日志"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.log_data, f, ensure_ascii=False, indent=2)
    
    def _get_tool_category(self, tool_name: str) -> str:
        """确定工具类别"""
        definitions = self.config.get("limit_definitions", {})
        
        for category, tools in definitions.items():
            if tool_name.lower() in [t.lower() for t in tools]:
                return category
        
        # 默认归类
        search_tools = ["search", "fetch", "browser"]
        finance_tools = ["finance", "datasource", "stock"]
        
        name_lower = tool_name.lower()
        if any(s in name_lower for s in search_tools):
            return "search"
        elif any(f in name_lower for f in finance_tools):
            return "finance"
        else:
            return "other"
    
    def _get_today_key(self) -> str:
        """获取今日日期键"""
        return datetime.now().strftime("%Y-%m-%d")
    
    def count(self, tool_name: str, details: str = "") -> Dict:
        """
        记录一次工具调用
        
        Args:
            tool_name: 工具名称（如 kimi_search, kimi_finance）
            details: 可选详情（如搜索关键词）
        
        Returns:
            计数结果
        """
        today = self._get_today_key()
        category = self._get_tool_category(tool_name)
        
        # 初始化今日记录
        if today not in self.log_data["daily_logs"]:
            self.log_data["daily_logs"][today] = {
                "total": 0,
                "by_category": {},
                "calls": []
            }
        
        day_log = self.log_data["daily_logs"][today]
        
        # 更新计数
        day_log["total"] += 1
        day_log["by_category"][category] = day_log["by_category"].get(category, 0) + 1
        
        # 记录详情
        call_record = {
            "time": datetime.now().isoformat(),
            "tool": tool_name,
            "category": category,
            "details": details
        }
        day_log["calls"].append(call_record)
        
        # 保存
        self._save_log()
        
        # 返回状态
        limit = self.config["daily_limits"].get(category, 100)
        used = day_log["by_category"].get(category, 0)
        remaining = max(0, limit - used)
        usage_ratio = used / limit if limit > 0 else 0
        
        return {
            "tool": tool_name,
            "category": category,
            "today_total": day_log["total"],
            "category_used": used,
            "category_limit": limit,
            "category_remaining": remaining,
            "usage_ratio": round(usage_ratio, 3),
            "status": self._status_from_ratio(usage_ratio)
        }
    
    def _status_from_ratio(self, ratio: float) -> str:
        """根据使用比例确定状态"""
        warning = self.config.get("warning_threshold", 0.8)
        emergency = self.config.get("emergency_threshold", 0.95)
        
        if ratio >= emergency:
            return "EMERGENCY"
        elif ratio >= warning:
            return "WARNING"
        else:
            return "NORMAL"
    
    def get_today_usage(self) -> Dict:
        """
        获取今日使用量
        
        Returns:
            今日使用统计
        """
        today = self._get_today_key()
        day_log = self.log_data["daily_logs"].get(today, {
            "total": 0,
            "by_category": {},
            "calls": []
        })
        
        limits = self.config["daily_limits"]
        categories = {}
        total_limit = 0
        total_used = 0
        
        for category, limit in limits.items():
            used = day_log["by_category"].get(category, 0)
            ratio = used / limit if limit > 0 else 0
            total_limit += limit
            total_used += used
            
            categories[category] = {
                "used": used,
                "limit": limit,
                "remaining": max(0, limit - used),
                "ratio": round(ratio, 3),
                "status": self._status_from_ratio(ratio)
            }
        
        total_ratio = total_used / total_limit if total_limit > 0 else 0
        
        return {
            "date": today,
            "total_used": total_used,
            "total_limit": total_limit,
            "total_remaining": max(0, total_limit - total_used),
            "total_ratio": round(total_ratio, 3),
            "overall_status": self._status_from_ratio(total_ratio),
            "by_category": categories
        }
    
    def get_call_history(self, date: str = None, limit: int = 50) -> List[Dict]:
        """
        获取调用历史
        
        Args:
            date: 日期（YYYY-MM-DD），默认今日
            limit: 返回记录数
        """
        if date is None:
            date = self._get_today_key()
        
        day_log = self.log_data["daily_logs"].get(date, {})
        calls = day_log.get("calls", [])
        
        return calls[-limit:]  # 返回最近N条
    
    def cleanup_old_logs(self, keep_days: int = 30):
        """清理旧日志"""
        today = datetime.now().date()
        cutoff = today - timedelta(days=keep_days)
        
        to_remove = []
        for date_key in self.log_data["daily_logs"]:
            try:
                log_date = datetime.strptime(date_key, "%Y-%m-%d").date()
                if log_date < cutoff:
                    to_remove.append(date_key)
            except:
                pass
        
        for date_key in to_remove:
            del self.log_data["daily_logs"][date_key]
        
        if to_remove:
            self._save_log()
        
        return {"removed": len(to_remove), "kept": len(self.log_data["daily_logs"])}


# ═══════════════════════════════════════════════════════
# 便捷函数（全局单例）
# ═══════════════════════════════════════════════════════
_counter = None

def _get_counter() -> APICounter:
    global _counter
    if _counter is None:
        _counter = APICounter()
    return _counter

def count_tool_call(tool_name: str, details: str = "") -> Dict:
    """
    记录一次工具调用（便捷函数）
    
    使用示例:
        count_tool_call("kimi_search", "MLCC产业链分析")
        count_tool_call("kimi_finance", "查询 688126 实时价格")
    """
    counter = _get_counter()
    return counter.count(tool_name, details)

def get_today_usage() -> Dict:
    """获取今日使用量（便捷函数）"""
    counter = _get_counter()
    return counter.get_today_usage()

def get_call_history(date: str = None, limit: int = 50) -> List[Dict]:
    """获取调用历史（便捷函数）"""
    counter = _get_counter()
    return counter.get_call_history(date, limit)


# ═══════════════════════════════════════════════════════
# 测试
# ═══════════════════════════════════════════════════════
def run_tests():
    """运行测试"""
    import shutil
    
    # 使用临时文件测试
    test_workspace = Path("/tmp/api_counter_test")
    test_workspace.mkdir(exist_ok=True)
    
    # 复制配置
    config_src = Path("/root/.openclaw/workspace/skills/daguan/api_counter_config.json")
    config_dst = test_workspace / "skills" / "daguan" / "api_counter_config.json"
    config_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(config_src, config_dst)
    
    counter = APICounter(str(test_workspace))
    
    print("=" * 60)
    print("📊 API计数器测试")
    print("=" * 60)
    
    # 模拟调用
    tools = [
        ("kimi_search", "搜索MLCC产业链"),
        ("kimi_search", "搜索北交所标的"),
        ("kimi_finance", "查询688126价格"),
        ("kimi_finance", "查询603663价格"),
        ("web_fetch", "获取网页内容"),
    ]
    
    for tool, detail in tools:
        result = counter.count(tool, detail)
        status_emoji = {"NORMAL": "✅", "WARNING": "⚠️", "EMERGENCY": "🚨"}
        emoji = status_emoji.get(result["status"], "➖")
        print(f"\n{emoji} {tool} → {result['category']}")
        print(f"   今日总计: {result['today_total']}")
        print(f"   类别: {result['category_used']}/{result['category_limit']} ({result['usage_ratio']*100:.1f}%)")
        print(f"   状态: {result['status']}")
    
    # 查询今日用量
    print("\n" + "=" * 60)
    print("📈 今日用量汇总")
    print("=" * 60)
    
    usage = counter.get_today_usage()
    print(f"\n总用量: {usage['total_used']} / {usage['total_limit']}")
    print(f"总比例: {usage['total_ratio']*100:.1f}%")
    print(f"整体状态: {usage['overall_status']}")
    
    print("\n分类详情:")
    for cat, data in usage['by_category'].items():
        emoji = "✅" if data['status'] == "NORMAL" else "⚠️" if data['status'] == "WARNING" else "🚨"
        print(f"  {emoji} {cat}: {data['used']}/{data['limit']} ({data['ratio']*100:.1f}%) [{data['status']}]")
    
    # 调用历史
    print("\n" + "=" * 60)
    print("📝 最近调用记录")
    print("=" * 60)
    
    history = counter.get_call_history(limit=5)
    for call in history:
        print(f"  [{call['time'][11:19]}] {call['tool']} → {call['details']}")
    
    print("=" * 60)
    
    # 清理测试文件
    shutil.rmtree(test_workspace)
    print("\n✅ 测试完成，临时文件已清理")


if __name__ == "__main__":
    run_tests()
