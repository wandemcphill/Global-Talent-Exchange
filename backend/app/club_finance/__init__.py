from app.club_finance.service import ClubFinanceError, ClubFinanceService

__all__ = ["ClubFinanceError", "ClubFinanceService"]


def __getattr__(name: str):
    if name == "router":
        from app.club_finance.router import router

        return router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
