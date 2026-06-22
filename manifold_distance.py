#!/usr/bin/env python3
"""
Manifold Distance - 流形距离评估
量化用户输入与当前关注域的偏离度

核心理念：用户有一个"关注域"（持仓、兴趣、主线），输入偏离这个域越远，
处理优先级越低，投入资源越少。
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class ManifoldDistance:
    """
    流形距离评估器
    
    关注域定义：
    - 持仓标的（第1组5只 + 关注池27只）
    - 兴趣行业（北交所、MLCC、深海科技、半导体、新材料）
    - 当前主线（Kronos识别的板块）
    - 近期高频话题（最近3次对话主题）
    
    距离等级：
    - 核心（0-0.3）：与持仓/主线直接相关 → 最高优先级
    - 相关（0.3-0.6）：与兴趣行业相关 → 中等优先级
    - 边缘（0.6-0.9）：泛相关 → 低优先级，精简处理
    - 偏离（0.9-1.0）：无关 → 最低优先级，极简处理
    """
    
    def __init__(self, workspace: str = "/root/.openclaw/workspace"):
        self.workspace = Path(workspace)
        self.state_file = self.workspace / "skills" / "daguan" / "global_state.json"
        self.name_map_file = self.workspace / "skills" / "daguan" / "stock_name_map.json"
        
        # 加载名称映射
        self.stock_name_map = self._load_name_map()
        
        # 关注域（从中观扫描结果读取，这里做fallback）
        self.core_domain = {
            "holdings": ["688126", "603663", "603738", "603650", "300460"],  # 第1组
            "watch_pool": [],  # 从中观扫描读取
            "interests": ["北交所", "MLCC", "深海科技", "半导体", "新材料", "固态电池"],
            "recent_topics": []  # 从最近memory读取
        }
    
    def _load_name_map(self) -> Dict[str, List[str]]:
        """加载股票名称映射表"""
        if not self.name_map_file.exists():
            return {}
        
        try:
            with open(self.name_map_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 合并holdings和watch_pool的映射
            name_map = {}
            for section in ["holdings", "watch_pool"]:
                if section in data:
                    name_map.update(data[section])
            
            return name_map
        except Exception as e:
            print(f"⚠️ 名称映射加载失败: {e}")
            return {}
    
    # ═══════════════════════════════════════════════════════
    # 距离计算
    # ═══════════════════════════════════════════════════════
    def calculate_distance(self, user_input: str) -> Dict:
        """
        计算输入与关注域的流形距离
        
        Returns:
            距离评估报告
        """
        # 加载最新关注域
        self._load_domain()
        
        distances = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "core_distance": 1.0,  # 与核心持仓的距离
            "interest_distance": 1.0,  # 与兴趣行业的距离
            "topic_distance": 1.0,  # 与近期话题的距离
            "overall_distance": 1.0,  # 综合距离
            "distance_level": "deviated",  # core / related / peripheral / deviated
            "matching_items": [],
            "recommendation": ""
        }
        
        # 1. 计算与核心持仓的距离
        core_dist, core_matches = self._calculate_stock_distance(
            user_input, self.core_domain["holdings"]
        )
        # 核心持仓命中 → 直接赋予低距离
        if core_matches:
            core_dist = 0.0
        distances["core_distance"] = core_dist
        
        # 2. 计算与关注池的距离
        watch_dist, watch_matches = self._calculate_stock_distance(
            user_input, self.core_domain["watch_pool"]
        )
        # 关注池命中 → 中等距离
        if watch_matches:
            watch_dist = 0.3
        distances["watch_distance"] = watch_dist
        
        # 3. 计算与兴趣行业的距离
        interest_dist, interest_matches = self._calculate_keyword_distance(
            user_input, self.core_domain["interests"]
        )
        distances["interest_distance"] = interest_dist
        
        # 4. 计算与近期话题的距离
        topic_dist, topic_matches = self._calculate_keyword_distance(
            user_input, self.core_domain["recent_topics"]
        )
        distances["topic_distance"] = topic_dist
        
        # 5. 综合距离（改进版：关注命中维度，未命中维度惩罚降低）
        base_distance = min(core_dist, watch_dist, interest_dist, topic_dist)
        
        if base_distance < 1.0:
            # 命中了至少一个维度，给予距离优惠
            match_count = sum(1 for d in [core_dist, watch_dist, interest_dist, topic_dist] if d < 1.0)
            bonus = min(0.3, match_count * 0.1)
            distances["overall_distance"] = round(max(0, base_distance - bonus), 2)
        else:
            distances["overall_distance"] = 1.0
        
        # 6. 确定距离等级（调整阈值）
        distances["distance_level"] = self._level_from_distance(
            distances["overall_distance"]
        )
        
        # 7. 收集匹配项（去重并保持顺序）
        seen = set()
        all_matches = []
        for m in core_matches + watch_matches + interest_matches + topic_matches:
            if m not in seen:
                seen.add(m)
                all_matches.append(m)
        distances["matching_items"] = all_matches
        
        # 8. 生成建议
        distances["recommendation"] = self._generate_recommendation(
            distances["distance_level"],
            distances["matching_items"]
        )
        
        return distances
    
    def _calculate_stock_distance(self, text: str, stocks: List[str]) -> Tuple[float, List[str]]:
        """计算与股票列表的距离（支持代码和名称匹配）"""
        if not stocks:
            return 1.0, []
        
        matches = []
        
        # 1. 匹配6位代码
        for stock in stocks:
            if stock in text:
                matches.append(stock)
        
        # 2. 匹配名称（从stock_name_map映射）
        for code in stocks:
            if code in self.stock_name_map:
                names = self.stock_name_map[code]
                for name in names:
                    if name in text:
                        matches.append(code)
                        break
        
        # 去重并保持顺序
        seen = set()
        unique_matches = []
        for m in matches:
            if m not in seen:
                seen.add(m)
                unique_matches.append(m)
        
        # 距离 = 1 - (匹配数 / 总数) * 匹配权重
        if unique_matches:
            distance = max(0, 1 - (len(unique_matches) / min(len(stocks), 5)) * 0.8)
        else:
            distance = 1.0
        
        return round(distance, 2), unique_matches
    
    def _calculate_keyword_distance(self, text: str, keywords: List[str]) -> Tuple[float, List[str]]:
        """计算与关键词列表的距离"""
        if not keywords:
            return 1.0, []
        
        matches = []
        text_lower = text.lower()
        
        for kw in keywords:
            if kw.lower() in text_lower:
                matches.append(kw)
        
        if matches:
            distance = max(0, 1 - (len(matches) / min(len(keywords), 3)) * 0.6)
        else:
            distance = 1.0
        
        return round(distance, 2), matches
    
    def _level_from_distance(self, distance: float) -> str:
        """根据距离确定等级（调整阈值）"""
        if distance <= 0.3:
            return "core"  # 核心
        elif distance <= 0.6:
            return "related"  # 相关
        elif distance <= 0.85:
            return "peripheral"  # 边缘
        else:
            return "deviated"  # 偏离
    
    def _generate_recommendation(self, level: str, matches: List[str]) -> str:
        """生成处理建议"""
        if level == "core":
            return f"核心关注域命中（{', '.join(matches[:3])}），执行完整分析"
        elif level == "related":
            return f"相关域命中（{', '.join(matches[:3])}），标准深度处理"
        elif level == "peripheral":
            return f"边缘关联（{', '.join(matches[:3]) if matches else '无'}），精简处理"
        else:
            return "偏离关注域，极简处理或记录归档"
    
    # ═══════════════════════════════════════════════════════
    # 加载关注域
    # ═══════════════════════════════════════════════════════
    def _load_domain(self):
        """从全局状态加载关注域"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                meso = state.get("meso", {})
                
                # 读取关注池
                watch_pool = meso.get("watch_pool", [])
                if watch_pool:
                    self.core_domain["watch_pool"] = watch_pool
                
                # 读取用户画像
                profile = meso.get("user_profile", {})
                interests = profile.get("interests", [])
                if interests:
                    self.core_domain["interests"] = interests
                
                # 读取近期话题（新增）
                recent_topics = meso.get("recent_topics", [])
                if recent_topics:
                    self.core_domain["recent_topics"] = recent_topics
                
            except:
                pass
    
    # ═══════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════
    def get_domain_summary(self) -> Dict:
        """获取当前关注域摘要"""
        self._load_domain()
        
        return {
            "core_holdings": self.core_domain["holdings"],
            "watch_pool_count": len(self.core_domain["watch_pool"]),
            "interests": self.core_domain["interests"],
            "recent_topics": self.core_domain["recent_topics"]
        }


def main():
    import sys
    
    md = ManifoldDistance()
    
    if len(sys.argv) > 1:
        user_input = sys.argv[1]
        result = md.calculate_distance(user_input)
        
        print("=" * 60)
        print("📐 流形距离评估")
        print("=" * 60)
        print(f"输入: {result['user_input']}")
        print(f"综合距离: {result['overall_distance']}")
        print(f"距离等级: {result['distance_level']}")
        print()
        print("各维度距离:")
        print(f"  核心持仓: {result['core_distance']}")
        print(f"  兴趣行业: {result['interest_distance']}")
        print(f"  近期话题: {result['topic_distance']}")
        print()
        print(f"匹配项: {result['matching_items']}")
        print(f"建议: {result['recommendation']}")
        print("=" * 60)
        
    else:
        # 测试几个例子
        test_inputs = [
            "沪硅产业现在怎么样？",  # 核心持仓
            "北方铜业怎么看？",  # 关注池
            "国瓷材料分析",  # 关注池
            "Phase 3完成了吗？",  # 近期话题
            "MLCC产业链分析",  # 兴趣行业
            "今天天气怎么样？",  # 偏离
            "北交所",  # 兴趣
        ]
        
        print("=" * 60)
        print("📐 流形距离测试")
        print("=" * 60)
        
        for inp in test_inputs:
            result = md.calculate_distance(inp)
            print(f"\n输入: {inp}")
            print(f"  距离: {result['overall_distance']} | 等级: {result['distance_level']}")
            print(f"  建议: {result['recommendation']}")
        
        print("=" * 60)


if __name__ == "__main__":
    main()
