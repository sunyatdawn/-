#!/usr/bin/env python3
"""
Global State Cache Updater - 全局状态缓存更新器
每15分钟执行一次，更新 global_state.json，减少实时扫描延迟

执行: python3 global_state_cache.py [--force]
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict

class GlobalStateCache:
    """全局状态缓存管理器"""
    
    def __init__(self, workspace: str = "/root/.openclaw/workspace"):
        self.workspace = Path(workspace)
        self.state_file = self.workspace / "skills" / "daguan" / "global_state.json"
        self.cache_meta = self.workspace / "skills" / "daguan" / "cache_meta.json"
    
    def update(self, force: bool = False) -> Dict:
        """
        更新全局状态缓存
        
        Args:
            force: 强制更新，忽略时间间隔
        
        Returns:
            更新结果
        """
        now = datetime.now()
        
        # 检查上次更新时间
        if not force and self.cache_meta.exists():
            with open(self.cache_meta, 'r') as f:
                meta = json.load(f)
            last_update = datetime.fromisoformat(meta.get("last_update", "2000-01-01"))
            minutes_since = (now - last_update).total_seconds() / 60
            
            # 如果15分钟内已更新，跳过
            if minutes_since < 15:
                return {
                    "status": "skipped",
                    "reason": f"{minutes_since:.1f}分钟前已更新",
                    "next_update_in": f"{15 - minutes_since:.1f}分钟"
                }
        
        # 执行扫描器更新缓存
        try:
            result = subprocess.run(
                ["python3", str(self.workspace / "skills" / "daguan" / "multi_scale_scanner.py"), ""],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # 解析JSON输出
            output = result.stdout
            json_start = output.find("[JSON_BEGIN]")
            json_end = output.find("[JSON_END]")
            
            if json_start != -1 and json_end != -1:
                json_str = output[json_start + len("[JSON_BEGIN]"):json_end].strip()
                state_data = json.loads(json_str)
            else:
                state_data = {"error": "无法解析扫描器输出"}
            
            # 加载recent_topics并更新到state_data
            topics_file = self.workspace / "skills" / "daguan" / "recent_topics.json"
            if topics_file.exists():
                with open(topics_file, 'r', encoding='utf-8') as f:
                    topics_data = json.load(f)
                recent_topics = topics_data.get("topics", [])
            else:
                recent_topics = []
            
            # 确保meso字段存在并添加recent_topics
            if "meso" not in state_data:
                state_data["meso"] = {}
            state_data["meso"]["recent_topics"] = recent_topics
            
            # 保存更新后的状态到global_state.json
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
            
            # 更新元数据
            meta = {
                "last_update": now.isoformat(),
                "update_count": 0,
                "avg_update_time_ms": 0
            }
            
            if self.cache_meta.exists():
                with open(self.cache_meta, 'r') as f:
                    old_meta = json.load(f)
                meta["update_count"] = old_meta.get("update_count", 0) + 1
            
            with open(self.cache_meta, 'w') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            
            return {
                "status": "updated",
                "timestamp": now.isoformat(),
                "market_state": state_data.get("macro", {}).get("risk_level", "unknown"),
                "watch_pool_count": len(state_data.get("meso", {}).get("watch_pool", []))
            }
            
        except subprocess.TimeoutExpired:
            return {"status": "error", "reason": "扫描器超时"}
        except Exception as e:
            return {"status": "error", "reason": str(e)}
    
    def get_cache_status(self) -> Dict:
        """获取缓存状态"""
        if not self.cache_meta.exists():
            return {"status": "no_cache", "message": "缓存尚未创建"}
        
        with open(self.cache_meta, 'r') as f:
            meta = json.load(f)
        
        last_update = datetime.fromisoformat(meta["last_update"])
        minutes_since = (datetime.now() - last_update).total_seconds() / 60
        
        return {
            "status": "active" if minutes_since < 30 else "stale",
            "last_update": meta["last_update"],
            "minutes_since": round(minutes_since, 1),
            "update_count": meta["update_count"]
        }


def main():
    import sys
    
    cache = GlobalStateCache()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        result = cache.update(force=True)
    elif len(sys.argv) > 1 and sys.argv[1] == "--status":
        result = cache.get_cache_status()
    else:
        result = cache.update()
    
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
