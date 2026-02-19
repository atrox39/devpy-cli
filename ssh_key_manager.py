import base64
import os
import json
import stat
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SSHKeyManager:
  def __init__(self, storage_file='ssh_keys.enc'):
    self.storage_file = storage_file

  def _derive_key(self, passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
      algorithm=hashes.SHA256(),
      length=32,
      salt=salt,
      iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))

  def _load_data(self):
    if not os.path.exists(self.storage_file):
      return {}
    try:
      with open(self.storage_file, 'r', encoding='utf-8') as f:
        return json.load(f)
    except json.JSONDecodeError:
      return {}

  def _save_data(self, data):
    with open(self.storage_file, 'w', encoding='utf-8') as f:
      json.dump(data, f, ensure_ascii=False, indent=2)

    # Harden file permissions (read/write only for owner)
    try:
      os.chmod(self.storage_file, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
      pass

  def add_key(self, name, key_path, passphrase):
    if not os.path.exists(key_path):
      raise FileNotFoundError(f'Key file not found: {key_path}')

    with open(key_path, 'r', encoding='utf-8') as f:
      key_content = f.read()

    salt = os.urandom(16)
    key = self._derive_key(passphrase, salt)
    f = Fernet(key)
    encrypted_content = f.encrypt(key_content.encode()).decode('utf-8')

    data = self._load_data()
    data[name] = {'salt': base64.b64encode(salt).decode('utf-8'), 'content': encrypted_content}
    self._save_data(data)
    return True

  def get_key(self, name, passphrase):
    data = self._load_data()
    if name not in data:
      raise ValueError(f"Key '{name}' not found")

    record = data[name]
    salt = base64.b64decode(record['salt'])
    encrypted_content = record['content'].encode('utf-8')

    key = self._derive_key(passphrase, salt)
    f = Fernet(key)
    try:
      return f.decrypt(encrypted_content).decode('utf-8')
    except Exception:
      raise ValueError('Invalid passphrase or corrupted key data')

  def list_keys(self):
    data = self._load_data()
    return list(data.keys())

  def delete_key(self, name):
    data = self._load_data()
    if name in data:
      del data[name]
      self._save_data(data)
      return True
    return False
