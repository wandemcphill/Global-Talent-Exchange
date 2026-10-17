from __future__ import annotations


def inbox_body(sender: str | None, what: str | None, why: str | None) -> str:
    """In-world inbox copy from the decision's own facts.

    The console does not call an external model. The sender, the ask, and the
    reason are already known when the decision is created.
    """
    voice = (sender or "The club").strip() or "The club"
    lead = (what or "").strip()
    reason = (why or "").strip()
    if lead and reason:
        return f"{voice}: {lead} {reason}"
    if lead:
        return f"{voice}: {lead}"
    if reason:
        return f"{voice}: {reason}"
    return f"{voice}: Update from the club."
