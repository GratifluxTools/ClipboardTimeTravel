"""暗号化キーの管理。Windows では DPAPI でユーザー単位に保護し、他の OS では 0600 権限で保存する。"""
import base64
import os
import sys

from cryptography.fernet import Fernet

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class _Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    def _dpapi(data: bytes, protect: bool) -> bytes:
        buf = ctypes.create_string_buffer(data, len(data))
        inp = _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
        out = _Blob()
        crypt32 = ctypes.windll.crypt32
        fn = crypt32.CryptProtectData if protect else crypt32.CryptUnprotectData
        if not fn(ctypes.byref(inp), None, None, None, None, 0, ctypes.byref(out)):
            raise OSError("DPAPI の処理に失敗しました")
        try:
            return ctypes.string_at(out.pbData, out.cbData)
        finally:
            ctypes.windll.kernel32.LocalFree(out.pbData)
else:
    def _dpapi(data: bytes, protect: bool) -> bytes:  # 非Windowsでは素通し（ファイル権限で保護）
        return data


class Vault:
    def __init__(self, key_path: str):
        self._fernet = Fernet(self._load_or_create(key_path))

    def encrypt(self, data: bytes) -> bytes:
        return self._fernet.encrypt(data)

    def decrypt(self, token: bytes) -> bytes:
        return self._fernet.decrypt(token)

    @staticmethod
    def _load_or_create(path: str) -> bytes:
        if os.path.exists(path):
            with open(path, "rb") as fh:
                return _dpapi(base64.b64decode(fh.read()), protect=False)
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(base64.b64encode(_dpapi(key, protect=True)))
        if sys.platform != "win32":
            os.chmod(path, 0o600)
        return key
