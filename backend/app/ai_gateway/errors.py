from __future__ import annotations


class AiProviderError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code
