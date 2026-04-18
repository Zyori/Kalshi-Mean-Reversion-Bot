import base64
import time
from pathlib import Path

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from src.core.exceptions import AuthenticationError


class KalshiAuth(httpx.Auth):
    def __init__(self, key_id: str, private_key_path: Path) -> None:
        self.key_id = key_id
        try:
            with open(private_key_path, "rb") as f:
                key = serialization.load_pem_private_key(f.read(), password=None)
        except FileNotFoundError as e:
            raise AuthenticationError(f"Private key not found: {private_key_path}") from e
        except Exception as e:
            raise AuthenticationError(f"Failed to load private key: {e}") from e

        if not isinstance(key, RSAPrivateKey):
            raise AuthenticationError("Private key must be RSA")
        self.private_key = key

    def _sign(self, timestamp_ms: str, method: str, path: str) -> str:
        message = f"{timestamp_ms}{method}{path}".encode()
        signature = self.private_key.sign(
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("ascii")

    def auth_flow(self, request: httpx.Request):
        timestamp_ms = str(int(time.time() * 1000))
        # raw_path preserves the full path including /trade-api/v2 prefix
        path = request.url.raw_path.decode("utf-8").split("?")[0]
        signature = self._sign(timestamp_ms, request.method, path)

        request.headers["KALSHI-ACCESS-KEY"] = self.key_id
        request.headers["KALSHI-ACCESS-SIGNATURE"] = signature
        request.headers["KALSHI-ACCESS-TIMESTAMP"] = timestamp_ms
        yield request
