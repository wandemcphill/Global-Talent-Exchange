"""Credit a user's GTEX Coin wallet from the platform account (admin adjustment, no real money).

Usage: python scripts/admin_credit_wallet.py <email> <amount> "<memo>"
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.database import get_session_factory, load_model_modules  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit  # noqa: E402
from app.wallets.service import LedgerPosting, WalletService  # noqa: E402


def main(email: str, amount: str, memo: str) -> None:
    load_model_modules()
    value = Decimal(amount)
    with get_session_factory()() as session:
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            raise SystemExit(f"user not found: {email}")
        wallet = WalletService()
        user_account = wallet.get_user_account(session, user, LedgerUnit.COIN)
        platform = wallet.ensure_platform_account(session, LedgerUnit.COIN)
        wallet.append_transaction(
            session,
            postings=[LedgerPosting(account=platform, amount=-value), LedgerPosting(account=user_account, amount=value)],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            description=memo,
            actor=user,
            metadata={"real_money": False, "memo": memo},
        )
        session.commit()
        print("credited", value, "GTX to", email, "balance", wallet.get_balance(session, user_account))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
