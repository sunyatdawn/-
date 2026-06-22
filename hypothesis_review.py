#!/usr/bin/env python3
"""
Hypothesis Review - 假设定期回顾
每月1日自动执行，检查假设是否过期、需要重新验证

执行: python3 hypothesis_review.py [--daily|--monthly]
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

class HypothesisReview:
    """假设定期回顾器"""
    
    def __init__(self, workspace: str = "/root/.openclaw/workspace"):
        self.workspace = Path(workspace)
        self.hypothesis_file = self.workspace / "skills" / "daguan" / "hypotheses.json"
        self.review_log = self.workspace / "skills" / "daguan" / "review_log.json"
    
    def run_monthly_review(self) -> Dict:
        """
        月度回顾：检查所有假设，标记过期，生成回顾报告
        
        Returns:
            回顾报告
        """
        if not self.hypothesis_file.exists():
            return {"status": "no_data", "message": "没有假设数据"}
        
        with open(self.hypothesis_file, 'r') as f:
            data = json.load(f)
        
        hypotheses = data.get("hypotheses", [])
        now = datetime.now()
        
        review_result = {
            "review_date": now.isoformat(),
            "total_hypotheses": len(hypotheses),
            "expired": [],
            "needs_reverify": [],
            "stale_unverified": [],
            "valid": [],
            "actions": []
        }
        
        for h in hypotheses:
            status = h.get("status", "unverified")
            created = datetime.fromisoformat(h["created_at"])
            
            # 检查是否超过30天未验证
            days_old = (now - created).days
            
            if status == "verified":
                # 已验证假设：检查是否超过30天未重新验证
                last_verified = h.get("last_verified")
                if last_verified:
                    last_v = datetime.fromisoformat(last_verified)
                    days_since_verify = (now - last_v).days
                    
                    if days_since_verify > 30:
                        h["status"] = "needs_reverify"
                        review_result["needs_reverify"].append({
                            "id": h["id"],
                            "text": h["text"][:100],
                            "days_since_verify": days_since_verify
                        })
                    else:
                        review_result["valid"].append({
                            "id": h["id"],
                            "text": h["text"][:100]
                        })
                else:
                    # 已标记verified但无验证时间
                    review_result["valid"].append({
                        "id": h["id"],
                        "text": h["text"][:100]
                    })
                    
            elif status == "unverified":
                # 未验证假设：超过7天未验证则标记为stale
                if days_old > 7:
                    review_result["stale_unverified"].append({
                        "id": h["id"],
                        "text": h["text"][:100],
                        "days_old": days_old
                    })
                else:
                    review_result["valid"].append({
                        "id": h["id"],
                        "text": h["text"][:100]
                    })
                    
            elif status == "expired":
                review_result["expired"].append({
                    "id": h["id"],
                    "text": h["text"][:100]
                })
        
        # 生成行动建议
        if review_result["needs_reverify"]:
            review_result["actions"].append(
                f"有{len(review_result['needs_reverify'])}个已验证假设超过30天未重新验证，建议搜索最新数据确认"
            )
        
        if review_result["stale_unverified"]:
            review_result["actions"].append(
                f"有{len(review_result['stale_unverified'])}个假设超过7天未验证，建议尽快验证或删除"
            )
        
        # 保存回顾日志
        self._save_review(review_result)
        
        # 更新假设文件
        with open(self.hypothesis_file, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return review_result
    
    def run_daily_check(self) -> Dict:
        """
        每日检查：快速扫描，只检查紧急事项
        
        Returns:
            检查结果
        """
        if not self.hypothesis_file.exists():
            return {"status": "no_data"}
        
        with open(self.hypothesis_file, 'r') as f:
            data = json.load(f)
        
        hypotheses = data.get("hypotheses", [])
        now = datetime.now()
        
        urgent = []
        
        for h in hypotheses:
            if h.get("status") == "unverified":
                created = datetime.fromisoformat(h["created_at"])
                days_old = (now - created).days
                
                if days_old > 7:
                    urgent.append({
                        "id": h["id"],
                        "text": h["text"][:100],
                        "days_old": days_old,
                        "action": "需要验证或删除"
                    })
        
        return {
            "check_date": now.isoformat(),
            "urgent_count": len(urgent),
            "urgent_items": urgent
        }
    
    def _save_review(self, result: Dict):
        """保存回顾日志"""
        self.review_log.parent.mkdir(parents=True, exist_ok=True)
        
        # 读取已有日志
        logs = []
        if self.review_log.exists():
            with open(self.review_log, 'r') as f:
                logs = json.load(f)
        
        logs.append(result)
        
        # 只保留最近12个月的日志
        logs = logs[-12:]
        
        with open(self.review_log, 'w') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    
    def get_review_history(self) -> List[Dict]:
        """获取回顾历史"""
        if self.review_log.exists():
            with open(self.review_log, 'r') as f:
                return json.load(f)
        return []


def main():
    import sys
    
    reviewer = HypothesisReview()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--monthly":
        result = reviewer.run_monthly_review()
        print("=" * 60)
        print("📋 假设月度回顾报告")
        print("=" * 60)
        print(f"总假设数: {result['total_hypotheses']}")
        print(f"需重新验证: {len(result['needs_reverify'])}")
        print(f"过期未验证: {len(result['stale_unverified'])}")
        print(f"已过期: {len(result['expired'])}")
        print(f"有效: {len(result['valid'])}")
        
        if result["actions"]:
            print("\n🎯 行动建议:")
            for action in result["actions"]:
                print(f"  • {action}")
        
        print("=" * 60)
        
    elif len(sys.argv) > 1 and sys.argv[1] == "--daily":
        result = reviewer.run_daily_check()
        print("=" * 60)
        print("🔍 假设每日检查")
        print("=" * 60)
        print(f"紧急事项: {result['urgent_count']}")
        
        if result["urgent_items"]:
            print("\n⚠️ 需要处理:")
            for item in result["urgent_items"]:
                print(f"  • [{item['id']}] {item['text']}... ({item['days_old']}天未验证)")
        
        print("=" * 60)
        
    else:
        print("Usage:")
        print("  python3 hypothesis_review.py --daily    # 每日检查")
        print("  python3 hypothesis_review.py --monthly  # 月度回顾")


if __name__ == "__main__":
    main()
