from .router import install_exception_handlers, router
from .service import GlobalApiV1RuntimeUnavailableError, GlobalApiV1Service


def _legacy_rent_player_disabled(*args, **kwargs):
    raise GlobalApiV1RuntimeUnavailableError(
        "Legacy tournament rentals are disabled; use the NationalTeamTournamentService rental lifecycle."
    )


if not getattr(GlobalApiV1Service.rent_player, "_gtex_legacy_rental_disabled", False):
    _legacy_rent_player_disabled._gtex_legacy_rental_disabled = True
    GlobalApiV1Service.rent_player = _legacy_rent_player_disabled


__all__ = ["install_exception_handlers", "router"]
