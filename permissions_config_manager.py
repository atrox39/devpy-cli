import json
import os
import threading
import time
from datetime import datetime
from pathlib import Path

class PermissionConfigManager:
    def __init__(self, config_file='permissions_config.json'):
        self.config_file = config_file
        self.config = self._load_config()
        self._last_mtime = self._get_mtime()
        self._lock = threading.Lock()
        self._start_watcher()

    def _get_mtime(self):
        try:
            return os.path.getmtime(self.config_file)
        except OSError:
            return 0

    def _load_config(self):
        if not os.path.exists(self.config_file):
            return {
                "version": "1.0",
                "rules": []
            }
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"version": "1.0", "rules": []}

    def _save_config(self):
        with self._lock:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

    def _start_watcher(self):
        def watcher():
            while True:
                time.sleep(2)
                current_mtime = self._get_mtime()
                if current_mtime > self._last_mtime:
                    self._last_mtime = current_mtime
                    with self._lock:
                        print(f"[PermissionConfigManager] Reloading configuration from {self.config_file}")
                        self.config = self._load_config()
        
        t = threading.Thread(target=watcher, daemon=True)
        t.start()

    def add_rule(self, operation, decision, context=None, params=None):
        rule = {
            "operation": operation,
            "decision": decision,  # 'allow', 'deny', 'ask'
            "created_at": datetime.utcnow().isoformat() + "Z",
            "context": context or "",
            "params": params or {}
        }
        with self._lock:
            # Remove existing rules for same operation to avoid conflicts (simple priority: last wins)
            # Or we can implement a more complex priority system.
            # For now, let's append and filter during evaluation or replace.
            # Strategy: Replace if exact match on operation and params?
            # Let's just append for history, but get_decision will pick the latest relevant one.
            self.config["rules"].insert(0, rule) # Insert at beginning for higher priority
            self._save_config()
        return rule

    def get_decision(self, operation, params=None):
        with self._lock:
            for rule in self.config.get("rules", []):
                if rule.get("operation") == operation:
                    # Check params match if specified in rule
                    rule_params = rule.get("params", {})
                    if not rule_params:
                        return rule.get("decision")
                    
                    # If rule has params, all must match provided params
                    if params and all(params.get(k) == v for k, v in rule_params.items()):
                        return rule.get("decision")
        return None # No explicit rule found

    def list_rules(self):
        with self._lock:
            return self.config.get("rules", [])

    def reset_config(self):
        with self._lock:
            self.config = {"version": "1.0", "rules": []}
            self._save_config()
