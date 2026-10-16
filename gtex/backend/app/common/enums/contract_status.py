from __future__ import annotations

from enum import Enum


class ContractStatus(str, Enum):
    ACTIVE = "active"
    EXPIRING = "expiring"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    AGREED = "agreed"
