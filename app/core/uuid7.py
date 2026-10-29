"""Generador y validador de UUIDv7 monótono según RFC 9562."""

import secrets
import threading
import time
import uuid
from typing import Any

from app.core.exceptions import DomainValidationError

_lock = threading.Lock()
_last_ts_ms = 0
_counter = 0


def generate_uuid7() -> uuid.UUID:
    """Genera un UUID versión 7 monótono y ordenable temporalmente."""
    global _last_ts_ms, _counter
    with _lock:
        now_ms = time.time_ns() // 1_000_000
        if now_ms > _last_ts_ms:
            _last_ts_ms = now_ms
            _counter = 0
        else:
            _counter += 1
            if _counter >= (
                1 << 28
            ):  # Si el contador sobrepasa la capacidad, avanzar timestamp
                _last_ts_ms += 1
                _counter = 0

        # RFC 9562 UUIDv7 layout:
        # [0..47]: unix_ts_ms (48 bits)
        # [48..51]: ver = 0111 (4 bits = 7)
        # [52..63]: rand_a / sub-ms counter (12 bits)
        # [64..65]: var = 10 (2 bits)
        # [66..127]: rand_b / sub-counter (62 bits)
        ts_48 = _last_ts_ms & 0xFFFFFFFFFFFF
        ver_4 = 0x7
        seq_12 = (_counter >> 16) & 0xFFF
        var_2 = 0x2
        seq_16 = _counter & 0xFFFF
        rand_46 = secrets.randbits(46)
        seq_62 = (seq_16 << 46) | rand_46

        int_val = (
            (ts_48 << 80) | (ver_4 << 76) | (seq_12 << 64) | (var_2 << 62) | seq_62
        )
        return uuid.UUID(int=int_val)


def ensure_uuid7(val: Any) -> uuid.UUID:
    """Valida que un valor sea un UUIDv7 válido; de lo contrario lanza DomainValidationError."""
    if val is None:
        raise DomainValidationError("UUID cannot be None")
    if not isinstance(val, uuid.UUID):
        try:
            val = uuid.UUID(str(val))
        except Exception as exc:
            raise DomainValidationError(f"Invalid UUID string: {val}") from exc

    if val.version != 7:
        raise DomainValidationError(
            f"Expected UUID version 7, got version {val.version} ({val})"
        )

    return val
