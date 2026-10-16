from __future__ import annotations

from app.wallets.providers.base import GenericProviderAdapter


class CryptoFiatProviderAdapter(GenericProviderAdapter):
    def __init__(self) -> None:
        super().__init__(key="crypto_fiat", display_name="Crypto to Fiat Intake")


__all__ = ["CryptoFiatProviderAdapter"]
