"""
Application Logger - tracks processed links/emails to avoid duplicates
"""

import json
import logging
from pathlib import Path
from datetime import datetime

log = logging.getLogger("AgentLogger")


class AgentLogger:
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.data = self._load()

    def _load(self) -> dict:
        if self.log_path.exists():
            try:
                with open(self.log_path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"processed": {}, "stats": {"applied": 0, "emailed": 0, "failed": 0}}

    def _save(self):
        with open(self.log_path, "w") as f:
            json.dump(self.data, f, indent=2)

    def already_processed(self, key: str) -> bool:
        entry = self.data["processed"].get(key)
        if not entry:
            return False
        # Only skip if successfully applied or emailed
        return entry["status"] in ("applied", "emailed")

    def log(self, key: str, source: str, status: str, reason: str = ""):
        entry = {
            "source": source,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        if reason:
            entry["reason"] = reason
        self.data["processed"][key] = entry
        if status in self.data["stats"]:
            self.data["stats"][status] += 1
        self._save()
        detail = f" ({reason})" if reason else ""
        log.info(f"Logged: {key} → {status}{detail}")

    def print_stats(self):
        stats = self.data["stats"]
        total = len(self.data["processed"])
        print(f"\n📊 Stats: {total} total | ✅ {stats['applied']} applied | "
              f"📧 {stats['emailed']} emailed | ❌ {stats['failed']} failed")
