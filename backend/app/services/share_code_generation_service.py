from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
from typing import Iterable

from backend.app.common.enums.share_code_type import ShareCodeType
from backend.app.schemas.share_code_core import ShareCodeCore, ShareCodeGenerationRequest

_NON_ALPHANUMERIC = re.compile(r"[^A-Z0-9]+")


class ShareCodeGenerationError(ValueError):
    """Raised when a share code cannot be generated safely."""


@dataclass(slots=True)
class ShareCodeGenerationService:
    min_generated_length: int = 8

    def generate(
        self,
        request: ShareCodeGenerationRequest,
        *,
        existing_codes: Iterable[str] = (),
    ) -> ShareCodeCore:
        taken_codes = {code.strip().upper() for code in existing_codes if code.strip()}
        normalized_vanity = self._normalize_code(request.vanity_code) if request.vanity_code else None
        if normalized_vanity is not None:
            if normalized_vanity in taken_codes:
                raise ShareCodeGenerationError(f"Vanity share code {normalized_vanity} is already in use.")
            resolved_code = normalized_vanity
        else:
            resolved_code = self._build_generated_code(request, taken_codes)

        return ShareCodeCore(
            code=resolved_code,
            code_type=request.code_type,
            owner_user_id=request.owner_user_id,
            owner_creator_id=request.owner_creator_id,
            linked_competition_id=request.linked_competition_id,
            vanity_code=normalized_vanity,
            max_uses=request.max_uses,
            starts_at=request.starts_at,
            ends_at=request.ends_at,
            metadata_json=request.metadata_json,
        )

    def _build_generated_code(self, request: ShareCodeGenerationRequest, taken_codes: set[str]) -> str:
        prefix = {
            ShareCodeType.USER_REFERRAL: "USR",
            ShareCodeType.CREATOR_SHARE: "CRT",
            ShareCodeType.COMPETITION_INVITE: "INV",
            ShareCodeType.PROMO_CODE: "PRM",
        }[request.code_type]
        slug_source = request.owner_handle or request.linked_competition_id or request.owner_user_id or prefix
        normalized_slug = self._normalize_code(slug_source)[:6]
        digest = hashlib.sha1(
            "|".join(
                filter(
                    None,
                    (
                        request.code_type.value,
                        request.owner_user_id,
                        request.owner_creator_id,
                        request.linked_competition_id,
                        request.owner_handle,
                    ),
                )
            ).encode("utf-8")
        ).hexdigest().upper()
        base_code = f"{prefix}{normalized_slug}{digest[:4]}"
        base_code = base_code[: max(self.min_generated_length, len(base_code))]
        resolved = base_code
        suffix = 0
        while resolved in taken_codes:
            suffix += 1
            resolved = f"{base_code[:28]}{suffix:02d}"[-32:]
        return resolved

    def _normalize_code(self, value: str) -> str:
        normalized = _NON_ALPHANUMERIC.sub("", value.upper())
        if len(normalized) < 4:
            raise ShareCodeGenerationError("Share codes must contain at least four letters or digits after cleanup.")
        return normalized[:32]
