from __future__ import annotations

from enum import Enum


class TransferBidStatus(str, Enum):
    PENDING = "pending"
    DRAFT = "draft"
    SUBMITTED = "submitted"
    COUNTER = "counter"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    COMPLETED = "completed"
