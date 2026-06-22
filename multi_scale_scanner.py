#!/usr/bin/env python3
"""
Multi-Scale Scanner - Real-time Global Thinking Engine
多尺度循环验证 - 实时全局扫描器

执行时机: 每次用户输入后，回复前强制执行
延迟: 2-3秒
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class MultiScaleScanner:
    """
    多尺度循环验证实现
    宏观(Macro) / 中观(Meso) / 微观(Micro) 三层扫描
    """
    
    def __init__(self, workspace: str = "/root/.openclaw/workspace"):
        self.workspace = Path(workspace)
        self.gimdengine = self.workspace / "gimdengine"
        self.memory_dir = self.workspace / "memory"
        self.state_file = self.workspace / "skills" / "daguan" / "global_state.json"
        
    # ═══════════════════════════════════════════════════════
    # 宏观尺度 · 低频趋势 (Market State)
    # ═══════════════════════════════════════════════════════
    def scan_macro(self) -> Dict:
        """
        宏观扫描: 市场状态、主线板块、风险等级
        数据来源: market_snapshot (TickFlow)
        """
        macro = {
            "timestamp": datetime.now().isoformat(),
            "market_state": {},
            "kronos_signal": None,
            "risk_level": "unknown",
            "leading_sectors": []
        }
        
        # 1. 读取最新市场快照
        snapshot_dir = Path("/opt/gimd/harness/knowledge/entities/market_snapshot")
        if snapshot_dir.exists():
            snapshots = sorted(snapshot_dir.glob("MS_*.json"), reverse=True)
            if snapshots:
                with open(snapshots[0], 'r') as f:
                    data = json.load(f)
                    macro["market_state"] = {
                        "sh_index": data.get("000001.SH", {}),
                        "sz_index": data.get("399001.SZ", {}),
                        "cy_index": data.get("399006.SZ", {}),
                        "kc_index": data.get("000688.SH", {})
                    }
                    
                    # 简单风险判断
                    kc_change = data.get("000688.SH", {}).get("change_pct", 0)
                    if kc_change > 2:
                        macro["risk_level"] = "high_opportunity"
                    elif kc_change < -2:
                        macro["risk_level"] = "high_risk"
                    else:
                        macro["risk_level"] = "neutral"
        
        # 2. 读取Kronos信号（如果有）
        kronos_file = self.gimdengine / "skills" / "kronos_signal" / "data" / "latest_regime.json"
        if kronos_file.exists():
            try:
                with open(kronos_file, 'r') as f:
                    regime = json.load(f)
                    macro["kronos_signal"] = regime.get("regime", "unknown")
            except:
                pass
        
        return macro
    
    # ═══════════════════════════════════════════════════════
    # 中观尺度 · 中频结构 (User Profile + System State)
    # ═══════════════════════════════════════════════════════
    def scan_meso(self) -> Dict:
        """
        中观扫描: 用户持仓、系统状态、待办事项
        数据来源: HEARTBEAT.md, MEMORY.md, heartbeat-state.json
        """
        meso = {
            "timestamp": datetime.now().isoformat(),
            "watch_pool": [],
            "user_profile": {},
            "system_state": {},
            "pending_items": []
        }
        
        # 1. 读取关注池（从HEARTBEAT.md）
        heartbeat_file = self.workspace / "HEARTBEAT.md"
        if heartbeat_file.exists():
            content = heartbeat_file.read_text()
            # 提取关注池标的
            watch_pool = self._extract_watch_pool(content)
            meso["watch_pool"] = watch_pool
        
        # 2. 读取用户画像（从MEMORY.md）
        memory_file = self.workspace / "MEMORY.md"
        if memory_file.exists():
            content = memory_file.read_text()
            profile = self._extract_user_profile(content)
            meso["user_profile"] = profile
        
        # 3. 读取系统状态（从heartbeat-state.json）
        state_file = self.memory_dir / "heartbeat-state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    meso["system_state"] = {
                        "last_watch_scan": state.get("lastChecks", {}).get("watch_pool", "unknown"),
                        "pending_events": len(state.get("pending_events", [])),
                        "high_elasticity_today": state.get("high_elasticity_alerts_today", 0)
                    }
            except:
                pass
        
        return meso
    
    # ═══════════════════════════════════════════════════════
    # 微观尺度 · 高频细节 (Input Analysis)
    # ═══════════════════════════════════════════════════════
    def scan_micro(self, user_input: str) -> Dict:
        """
        微观扫描: 输入语义分析、意图识别、关联度判断
        """
        micro = {
            "timestamp": datetime.now().isoformat(),
            "input_type": "unknown",
            "keywords": [],
            "sentiment": "neutral",
            "urgency": "normal",
            "related_to_watch_pool": False,
            "related_to_positions": False
        }
        
        # 1. 输入类型识别（简化版意图路由）
        input_lower = user_input.lower()
        
        # 1.0 先检查是否为纯聊天话题（天气、时间、问候等）
        chat_topics = ["天气", "时间", "几点", "早上好", "晚上好", "你好", "hi", "hello", "在吗", "吃了吗", "谢谢", "拜拜"]
        if any(topic in input_lower for topic in chat_topics):
            micro["input_type"] = "general_chat"
        elif any(kw in input_lower for kw in ["什么情况", "怎么样了", "进度"]):
            micro["input_type"] = "status_query"
        elif any(kw in input_lower for kw in ["修复", "更新", "修改", "执行", "运行"]):
            micro["input_type"] = "operation_command"
        elif any(kw in input_lower for kw in ["分析", "怎么样", "看看", "查一下"]):
            micro["input_type"] = "analysis_request"
        elif any(kw in input_lower for kw in ["搜索", "找一下", "最新"]):
            micro["input_type"] = "search_request"
        else:
            micro["input_type"] = "general_chat"
        
        # 2. 关键词提取（简单的股票代码、公司名称匹配）
        # 提取6位数字（股票代码）
        codes = re.findall(r'\b\d{6}\b', user_input)
        micro["keywords"] = codes
        
        # 2.1 检查是否与关注池中的代码直接匹配（微观层也应扫描）
        # 先获取meso数据（watch_pool）
        meso = self.scan_meso()
        watch_pool = meso.get("watch_pool", [])
        if any(code in watch_pool for code in codes):
            micro["related_to_watch_pool"] = True
        
        # 3. 情绪判断
        if any(kw in input_lower for kw in [" urgent", "紧急", "马上", "立刻", "快"]):
            micro["urgency"] = "urgent"
        elif any(kw in input_lower for kw in ["不错", "很好", "ok", "赞"]):
            micro["sentiment"] = "positive"
        elif any(kw in input_lower for kw in ["不对", "错了", "不行", "差"]):
            micro["sentiment"] = "negative"
        
        return micro
    
    # ═══════════════════════════════════════════════════════
    # 全量扫描
    # ═══════════════════════════════════════════════════════
    def full_scan(self, user_input: str) -> Dict:
        """执行完整多尺度扫描"""
        result = {
            "scan_version": "1.0.0",
            "scan_time": datetime.now().isoformat(),
            "macro": self.scan_macro(),
            "meso": self.scan_meso(),
            "micro": self.scan_micro(user_input)
        }
        
        # 关联度判断
        result["global_assessment"] = self._assess_global_relevance(result)
        
        # 保存状态
        self._save_state(result)
        
        return result
    
    # ═══════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════
    def _extract_watch_pool(self, content: str) -> List[str]:
        """从HEARTBEAT.md提取关注池标的"""
        stocks = []
        # 匹配股票代码格式 (6位数字)
        codes = re.findall(r'\b(\d{6})\b', content)
        # 去重并限制数量
        seen = set()
        for code in codes:
            if code not in seen and len(stocks) < 30:
                seen.add(code)
                stocks.append(code)
        return stocks
    
    def _extract_user_profile(self, content: str) -> Dict:
        """从MEMORY.md提取用户画像"""
        profile = {
            "interests": [],
            "positions": [],
            "stage": "unknown"
        }
        
        # 提取活跃兴趣
        if "活跃兴趣" in content:
            interests_match = re.search(r'活跃兴趣.*?(?=##|\Z)', content, re.DOTALL)
            if interests_match:
                interests_text = interests_match.group(0)
                # 简单提取关键词
                keywords = ["北交所", "MLCC", "深海科技", "半导体", "新材料", "固态电池"]
                for kw in keywords:
                    if kw in interests_text:
                        profile["interests"].append(kw)
        
        return profile
    
    def _assess_global_relevance(self, result: Dict) -> Dict:
        """评估全局关联度"""
        assessment = {
            "relevance_level": "low",  # low / medium / high
            "reason": "",
            "action_required": False
        }
        
        micro = result["micro"]
        meso = result["meso"]
        
        # 判断关联度
        if micro["input_type"] == "operation_command":
            assessment["relevance_level"] = "high"
            assessment["reason"] = "系统操作指令，直接影响系统状态"
            assessment["action_required"] = True
        elif micro["input_type"] == "status_query":
            assessment["relevance_level"] = "medium"
            assessment["reason"] = "状态查询，需要读取系统状态"
            assessment["action_required"] = False
        elif micro["input_type"] in ["analysis_request", "search_request"]:
            # 检查是否与关注池相关
            keywords = micro.get("keywords", [])
            watch_pool = meso.get("watch_pool", [])
            
            if any(kw in watch_pool for kw in keywords):
                assessment["relevance_level"] = "high"
                assessment["reason"] = f"标的 {keywords} 在关注池中"
                assessment["action_required"] = True
            else:
                assessment["relevance_level"] = "medium"
                assessment["reason"] = "分析请求，需要搜索前置"
                assessment["action_required"] = True
        
        return assessment
    
    def _save_state(self, result: Dict):
        """保存扫描结果到全局状态文件"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════
# 命令行入口
# ═══════════════════════════════════════════════════════
def main():
    import sys
    
    scanner = MultiScaleScanner()
    
    # 如果有命令行参数，作为用户输入
    user_input = sys.argv[1] if len(sys.argv) > 1 else ""
    
    result = scanner.full_scan(user_input)
    
    # 输出简化版报告（用于调试）
    print("=" * 60)
    print("🌐 全局扫描完成")
    print("=" * 60)
    print(f"输入类型: {result['micro']['input_type']}")
    print(f"关联度: {result['global_assessment']['relevance_level']}")
    print(f"风险等级: {result['macro']['risk_level']}")
    print(f"关注池数量: {len(result['meso']['watch_pool'])}")
    print("=" * 60)
    
    # 输出完整JSON到stdout（供调用方解析）
    print("\n[JSON_BEGIN]")
    print(json.dumps(result, ensure_ascii=False))
    print("[JSON_END]")


if __name__ == "__main__":
    main()
