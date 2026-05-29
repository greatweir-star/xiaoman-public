"""秘密字段加密存储 — MVP 使用 Fernet 风格对称加密（stdlib）"""

from __future__ import annotations

import base64
import hashlib
import os
from typing import Any


def _derive_key(user_id: str) -> bytes:
    secret = os.getenv("XIAOMAN_SECRET_KEY", "xiaoman-dev-secret-change-me")
    digest = hashlib.sha256(f"{secret}:{user_id}".encode()).digest()
    return base64.urlsafe_b64encode(digest)


class SecretVault:
    """对用户秘密做可逆加密（按 user_id 派生密钥）"""

    @staticmethod
    def encrypt(plaintext: str, user_id: str) -> str:
        if not plaintext:
            return ""
        key = _derive_key(user_id)
        data = plaintext.encode("utf-8")
        xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
        return "enc:" + base64.urlsafe_b64encode(xored).decode("ascii")

    @staticmethod
    def decrypt(ciphertext: str, user_id: str) -> str:
        if not ciphertext or not ciphertext.startswith("enc:"):
            return ciphertext
        key = _derive_key(user_id)
        raw = base64.urlsafe_b64decode(ciphertext[4:].encode("ascii"))
        plain = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
        return plain.decode("utf-8")

    @staticmethod
    def redact_for_display(secret_record: dict[str, Any], user_id: str, reveal: bool = False) -> dict[str, Any]:
        out = dict(secret_record)
        enc = out.get("content_encrypted") or out.get("content", "")
        if reveal:
            out["content"] = SecretVault.decrypt(enc, user_id)
        else:
            out["content"] = "🔒 已加密保存"
        return out
