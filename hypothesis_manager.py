#!/usr/bin/env python3
"""
Hypothesis Manager - 假设生命周期管理
管理假设的创建、验证、回顾和失效
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

class HypothesisManager:
    """假设管理器 - 实现锚点回溯和假设审查"""
    
    def __init__(self, workspace: str = "/root/.openclaw/workspace"):
        self.workspace = Path(workspace)
        self.hypothesis_file = self.workspace / "skills" / "daguan" / "hypotheses.json"
        self.hypotheses = self._load_hypotheses()
    
    def _load_hypotheses(self) -> Dict:
        """加载已有假设"""
        if self.hypothesis_file.exists():
            with open(self.hypothesis_file, 'r') as f:
                return json.load(f)
        return {"hypotheses": [], "last_review": None}
    
    def _save_hypotheses(self):
        """保存假设"""
        self.hypothesis_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.hypothesis_file, 'w') as f:
            json.dump(self.hypotheses, f, ensure_ascii=False, indent=2)
    
    def track_assumption(self, text: str, source: str, status: str = "unverified") -> str:
        """
        追踪一个新假设
        
        Args:
            text: 假设内容
            source: 来源（memory/search/user/document）
            status: unverified / verified / uncertain / expired
        
        Returns:
            assumption_id: 假设ID
        """
        assumption_id = f"A{len(self.hypotheses['hypotheses']) + 1:04d}"
        
        hypothesis = {
            "id": assumption_id,
            "text": text,
            "source": source,
            "status": status,
            "created_at": datetime.now().isoformat(),
            "last_verified": None,
            "expiry_date": (datetime.now() + timedelta(days=30)).isoformat(),
            "verification_sources": [],
            "falsification_conditions": []  # 什么情况下这个假设失效
        }
        
        self.hypotheses["hypotheses"].append(hypothesis)
        self._save_hypotheses()
        
        return assumption_id
    
    def verify_assumption(self, assumption_id: str, verification_source: str) -> bool:
        """验证一个假设"""
        for h in self.hypotheses["hypotheses"]:
            if h["id"] == assumption_id:
                h["status"] = "verified"
                h["last_verified"] = datetime.now().isoformat()
                h["verification_sources"].append(verification_source)
                self._save_hypotheses()
                return True
        return False
    
    def review_all(self) -> List[Dict]:
        """
        回顾所有假设，返回需要关注的假设
        
        Returns:
            List of hypotheses that need attention
        """
        needs_attention = []
        now = datetime.now()
        
        for h in self.hypotheses["hypotheses"]:
            # 检查是否过期
            expiry = datetime.fromisoformat(h["expiry_date"])
            if now > expiry and h["status"] == "verified":
                h["status"] = "needs_reverify"
                needs_attention.append({
                    "hypothesis": h,
                    "reason": "超过30天未重新验证"
                })
            
            # 检查未验证假设
            if h["status"] == "unverified":
                needs_attention.append({
                    "hypothesis": h,
                    "reason": "从未验证"
                })
        
        self.hypotheses["last_review"] = now.isoformat()
        self._save_hypotheses()
        
        return needs_attention
    
    def check_anchor(self, conclusion: str, supporting_facts: List[str]) -> Dict:
        """
        锚点回溯检查
        
        Args:
            conclusion: 结论
            supporting_facts: 支撑事实列表
        
        Returns:
            anchor_check result
        """
        result = {
            "conclusion": conclusion,
            "facts_count": len(supporting_facts),
            "facts": supporting_facts,
            "anchor_strength": "strong" if len(supporting_facts) >= 2 else "weak",
            "logic_gaps": [],
            "recommendation": ""
        }
        
        # 检查逻辑跳跃
        if len(supporting_facts) == 0:
            result["logic_gaps"].append("结论无任何事实支撑")
            result["anchor_strength"] = "none"
        elif len(supporting_facts) == 1:
            result["logic_gaps"].append("仅有一个事实支撑，可能存在逻辑跳跃")
        
        # 建议
        if result["anchor_strength"] == "weak":
            result["recommendation"] = "需要更多事实支撑或标注为假设"
        
        return result
    
    def get_recent_hypotheses(self, days: int = 7) -> List[Dict]:
        """
        获取最近N天的活跃假设（跨会话自动加载用）
        
        Args:
            days: 最近N天，默认7天
        
        Returns:
            List of recent hypotheses
        """
        now = datetime.now()
        cutoff = now - timedelta(days=days)
        
        recent = []
        for h in self.hypotheses["hypotheses"]:
            created = datetime.fromisoformat(h["created_at"])
            if created > cutoff:
                recent.append(h)
        
        # 按创建时间倒序
        recent.sort(key=lambda x: x["created_at"], reverse=True)
        return recent
    
    def load_recent_for_session(self, days: int = 7) -> str:
        """
        生成跨会话假设摘要（用于prompt注入）
        
        Returns:
            假设摘要文本，可直接注入系统提示
        """
        recent = self.get_recent_hypotheses(days)
        if not recent:
            return ""
        
        lines = [f"\n[大观·活跃假设] 最近{days}天未验证假设："]
        for h in recent[:5]:  # 最多5条
            status_icon = "❓" if h["status"] == "unverified" else "✅" if h["status"] == "verified" else "⚠️"
            lines.append(f"  {status_icon} {h['id']}: {h['text']} [{h['status']}]")
        
        return "\n".join(lines)
    
    def get_pending_verifications(self) -> List[Dict]:
        """获取所有待验证假设"""
        return [h for h in self.hypotheses["hypotheses"] if h["status"] in ["unverified", "uncertain"]]


def main():
    """命令行测试"""
    manager = HypothesisManager()
    
    # 测试追踪假设
    aid = manager.track_assumption(
        "利元亨固态电池设备订单排至2027年",
        "industry_report",
        "unverified"
    )
    print(f"创建假设: {aid}")
    
    # 测试锚点检查
    result = manager.check_anchor(
        "利元亨是固态电池设备龙头",
        ["公司公告提及固态电池设备", "行业报告提及"]  # 支持事实
    )
    print(f"锚点强度: {result['anchor_strength']}")
    
    # 查看待验证
    pending = manager.get_pending_verifications()
    print(f"待验证假设: {len(pending)}")


if __name__ == "__main__":
    main()
