from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CommonSchema(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        use_enum_values=False,
    )
