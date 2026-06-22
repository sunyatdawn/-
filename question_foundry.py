#!/usr/bin/env python3
"""
Question Foundry - 问题铸造器
从残留异常和流形空洞中生成更深层的新问题

执行时机:
1. 每次用户交互结束后（由Agent调用）
2. 每天汇总一次（cron定时任务）
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class QuestionFoundry:
    """
    问题铸造器
    核心理念：从每次交互的"残留异常"中提炼出值得深挖的新问题
    """
    
    def __init__(self, workspace: str = "/root/.openclaw/workspace"):
        self.workspace = Path(workspace)
        self.pending_file = self.workspace / "memory" / "pending_questions.json"
        self.session_history_dir = self.workspace / "memory"
        
    # ═══════════════════════════════════════════════════════
    # 收集残留异常
    # ═══════════════════════════════════════════════════════
    def collect_residuals(self, session_text: str = "", user_input: str = "") -> List[Dict]:
        """
        从会话文本中提取残留异常
        
        残留异常类型：
        1. 未完全回答的问题（用户追问、未决事项）
        2. 标注为 [ASSUMPTION:不确定] 的假设
        3. 用户未选择的分支选项（如A/B/C/D选择）
        4. 搜索中发现但未深入的新信息
        5. 时间敏感但已过期的信息
        """
        residuals = []
        
        # 1. 检测未决假设
        uncertain_assumptions = re.findall(
            r'\[ASSUMPTION:不确定\](.*?)(?=\n|$)',
            session_text,
            re.DOTALL
        )
        for assumption in uncertain_assumptions:
            residuals.append({
                "type": "uncertain_assumption",
                "content": assumption.strip(),
                "priority": "high",
                "reason": "假设未验证，需要搜索确认"
            })
        
        # 2. 检测用户未选择的分支
        branch_patterns = [
            r'选项[：:]\s*([A-E][、.].*?)(?=\n|$)',
            r'([A-E])[、.]\s*(.*?)(?=\n|$)',
        ]
        for pattern in branch_patterns:
            branches = re.findall(pattern, session_text)
            if branches and len(branches) >= 2:
                # 检查是否有明确的选择结果
                has_selection = any(
                    kw in session_text for kw in ['选择', '选', '决定', '确定']
                )
                if not has_selection:
                    residuals.append({
                        "type": "unselected_branch",
                        "content": str(branches),
                        "priority": "medium",
                        "reason": "用户未做出选择，需要跟进"
                    })
        
        # 3. 检测未完成的任务
        todo_patterns = [
            r'待办[：:](.*?)(?=\n|$)',
            r'TODO[：:](.*?)(?=\n|$)',
            r'后续[：:](.*?)(?=\n|$)',
        ]
        for pattern in todo_patterns:
            todos = re.findall(pattern, session_text, re.DOTALL)
            for todo in todos:
                residuals.append({
                    "type": "pending_task",
                    "content": todo.strip(),
                    "priority": "high",
                    "reason": "明确的待办事项"
                })
        
        # 4. 检测问题标记（用户说"什么意思"、"说清楚"等）
        confusion_signals = ['什么意思', '说清楚', '再说一遍', '不太明白', '没有理解']
        for signal in confusion_signals:
            if signal in user_input:
                residuals.append({
                    "type": "clarification_needed",
                    "content": user_input,
                    "priority": "high",
                    "reason": f"用户表达困惑：{signal}"
                })
        
        # 5. 检测"以后再说"、"暂时不需要"
        defer_signals = ['以后再说', '暂时不需要', '先放一放', '下次']
        for signal in defer_signals:
            if signal in session_text:
                residuals.append({
                    "type": "deferred_topic",
                    "content": "用户主动推迟的话题",
                    "priority": "low",
                    "reason": f"用户推迟：{signal}"
                })
        
        return residuals
    
    # ═══════════════════════════════════════════════════════
    # 铸造新问题
    # ═══════════════════════════════════════════════════════
    def forge_questions(self, residuals: List[Dict], context: Dict = None) -> List[Dict]:
        """
        从残留异常中铸造新问题
        
        铸造规则：
        1. 不确定假设 → "验证[假设内容]的具体来源"
        2. 未选择分支 → "跟进用户未选择的[选项内容]"
        3. 待办任务 → "完成[任务内容]"
        4. 需要澄清 → "重新解释[内容]，使用更简单的语言"
        5. 推迟话题 → "在适当时机重新提起[话题]"
        """
        questions = []
        
        for residual in residuals:
            question = {
                "id": f"Q{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(questions):03d}",
                "created_at": datetime.now().isoformat(),
                "source_type": residual["type"],
                "source_content": residual["content"][:200],  # 限制长度
                "priority": residual["priority"],
                "status": "pending",
                "forged_question": "",
                "context": context or {},
                "auto_push": False,
                "push_conditions": []
            }
            
            if residual["type"] == "uncertain_assumption":
                question["forged_question"] = f"验证假设：{residual['content'][:100]}..."
                question["auto_push"] = True
                question["push_conditions"] = ["用户下次提到相关标的", "市场出现相关催化"]
                
            elif residual["type"] == "unselected_branch":
                question["forged_question"] = f"跟进用户未选择的选项"
                question["auto_push"] = False
                question["push_conditions"] = ["用户再次询问相关主题"]
                
            elif residual["type"] == "pending_task":
                question["forged_question"] = f"完成待办：{residual['content'][:100]}..."
                question["auto_push"] = True
                question["push_conditions"] = ["用户下次询问进度", "定时提醒（24小时后）"]
                
            elif residual["type"] == "clarification_needed":
                question["forged_question"] = f"重新解释：{residual['content'][:100]}..."
                question["auto_push"] = False
                question["push_conditions"] = ["用户再次提到相关概念"]
                
            elif residual["type"] == "deferred_topic":
                question["forged_question"] = f"跟进推迟的话题"
                question["auto_push"] = False
                question["push_conditions"] = ["市场出现相关催化", "一周后主动提醒"]
            
            questions.append(question)
        
        return questions
    
    # ═══════════════════════════════════════════════════════
    # 评估优先级
    # ═══════════════════════════════════════════════════════
    def assess_priority(self, question: Dict, user_context: Dict) -> str:
        """
        评估问题优先级
        
        高优先级：
        - 与用户当前持仓/主线相关
        - 系统稳定性问题
        - 用户明确要求的待办
        
        中优先级：
        - 与分析框架相关
        - 知识基线更新
        
        低优先级：
        - 一般性知识问题
        - 用户推迟的话题
        """
        # 检查是否与用户持仓相关
        watch_pool = user_context.get("watch_pool", [])
        question_text = question.get("forged_question", "")
        
        # 简单关键词匹配
        for code in watch_pool:
            if code in question_text:
                return "high"
        
        # 根据source_type判断
        priority_map = {
            "uncertain_assumption": "high",
            "pending_task": "high",
            "clarification_needed": "medium",
            "unselected_branch": "medium",
            "deferred_topic": "low"
        }
        
        return priority_map.get(question["source_type"], "low")
    
    # ═══════════════════════════════════════════════════════
    # 更新待办问题
    # ═══════════════════════════════════════════════════════
    def update_pending(self, new_questions: List[Dict]):
        """更新待办问题列表"""
        existing = self._load_pending()
        
        # 去重：基于source_content
        existing_contents = {q["source_content"] for q in existing["questions"]}
        
        for q in new_questions:
            if q["source_content"] not in existing_contents:
                existing["questions"].append(q)
                existing_contents.add(q["source_content"])
        
        # 清理已完成的问题
        existing["questions"] = [
            q for q in existing["questions"] 
            if q["status"] != "completed"
        ]
        
        existing["last_update"] = datetime.now().isoformat()
        self._save_pending(existing)
    
    # ═══════════════════════════════════════════════════════
    # 获取高优先级问题（用于推送）
    # ═══════════════════════════════════════════════════════
    def get_push_candidates(self, limit: int = 5) -> List[Dict]:
        """获取需要主动推送的问题"""
        pending = self._load_pending()
        
        candidates = [
            q for q in pending["questions"]
            if q["status"] == "pending" 
            and q["auto_push"]
            and q["priority"] == "high"
        ]
        
        # 按创建时间排序，最新的在前
        candidates.sort(key=lambda x: x["created_at"], reverse=True)
        
        return candidates[:limit]
    
    # ═══════════════════════════════════════════════════════
    # 标记完成
    # ═══════════════════════════════════════════════════════
    def mark_completed(self, question_id: str):
        """标记问题为已完成"""
        pending = self._load_pending()
        
        for q in pending["questions"]:
            if q["id"] == question_id:
                q["status"] = "completed"
                q["completed_at"] = datetime.now().isoformat()
                break
        
        self._save_pending(pending)
    
    # ═══════════════════════════════════════════════════════
    # 辅助方法
    # ═══════════════════════════════════════════════════════
    def _load_pending(self) -> Dict:
        """加载待办问题"""
        if self.pending_file.exists():
            with open(self.pending_file, 'r') as f:
                return json.load(f)
        return {
            "questions": [],
            "last_update": None,
            "total_forged": 0
        }
    
    def _save_pending(self, data: Dict):
        """保存待办问题"""
        self.pending_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pending_file, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    # ═══════════════════════════════════════════════════════
    # 全量流程（单次交互后调用）
    # ═══════════════════════════════════════════════════════
    def process_session(self, session_text: str, user_input: str, context: Dict = None) -> List[Dict]:
        """
        处理单次会话，生成新问题
        
        Returns:
            新生成的问题列表
        """
        # 1. 收集残留异常
        residuals = self.collect_residuals(session_text, user_input)
        
        if not residuals:
            return []
        
        # 2. 铸造问题
        questions = self.forge_questions(residuals, context)
        
        # 3. 评估优先级
        for q in questions:
            q["priority"] = self.assess_priority(q, context or {})
        
        # 4. 更新待办
        self.update_pending(questions)
        
        return questions


# ═══════════════════════════════════════════════════════
# 命令行入口
# ═══════════════════════════════════════════════════════
def main():
    import sys
    
    foundry = QuestionFoundry()
    
    # 测试模式
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_session = """
        用户：利元亨现在怎么样？
        AI：利元亨（688499）是固态电池设备...
        [ASSUMPTION:不确定] 利元亨固态电池设备订单排至2027年
        用户：什么意思？
        AI：就是...
        用户：以后再说
        """
        
        questions = foundry.process_session(
            test_session, 
            "以后再说",
            {"watch_pool": ["688499"]}
        )
        
        print("=" * 60)
        print("🔨 问题铸造完成")
        print("=" * 60)
        print(f"生成问题数: {len(questions)}")
        for q in questions:
            print(f"\n[{q['priority'].upper()}] {q['forged_question']}")
            print(f"  来源: {q['source_type']}")
            print(f"  自动推送: {'是' if q['auto_push'] else '否'}")
        print("=" * 60)
        
        # 查看待办
        pending = foundry._load_pending()
        print(f"\n待办问题总数: {len(pending['questions'])}")
        
    # 获取推送候选
    elif len(sys.argv) > 1 and sys.argv[1] == "--push":
        candidates = foundry.get_push_candidates()
        print("=" * 60)
        print("📤 推送候选")
        print("=" * 60)
        for c in candidates:
            print(f"[{c['priority']}] {c['forged_question']}")
        
    else:
        print("Usage:")
        print("  python3 question_foundry.py --test    # 测试模式")
        print("  python3 question_foundry.py --push    # 获取推送候选")


if __name__ == "__main__":
    main()
