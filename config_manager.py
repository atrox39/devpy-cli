import json
import os

class ConfigManager:
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_file):
            return {
                'mode': 'local',
                'ssh': {
                    'host': '',
                    'user': '',
                    'key_name': ''
                }
            }
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {'mode': 'local'}

    def save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2)

    def set_mode(self, mode):
        if mode not in ['local', 'ssh']:
            raise ValueError("Mode must be 'local' or 'ssh'")
        self.config['mode'] = mode
        self.save_config()

    def get_mode(self):
        return self.config.get('mode', 'local')

    def set_ssh_config(self, host, user, key_name):
        self.config['ssh'] = {
            'host': host,
            'user': user,
            'key_name': key_name
        }
        self.save_config()

    def get_ssh_config(self):
        return self.config.get('ssh', {})
