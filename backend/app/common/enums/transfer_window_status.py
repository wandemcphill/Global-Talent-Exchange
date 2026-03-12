from __future__ import annotations

from enum import Enum


class TransferWindowStatus(str, Enum):
    UPCOMING = "upcoming"
    OPEN = "open"
    CLOSED = "closed"
