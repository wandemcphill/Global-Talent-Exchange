from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.pundits.analysis import analyze_match
from app.pundits.debate import DebateGenerator
from app.pundits.formatter import build_headline
from app.pundits.hot_takes import generate_hot_takes
from app.pundits.personas import PUNDITS
from app.pundits.schemas import (
    PunditDebateLineView,
    PunditDebateResponse,
    PunditMatchAnalysisView,
    PunditPersonaView,
)
from app.viral.service import load_replay_payload


@dataclass(slots=True)
class PunditService:
    session: Session
    settings: Settings | None = None
    debate_generator: DebateGenerator | None = None

    def __post_init__(self) -> None:
        if self.settings is None:
            self.settings = get_settings()
        if self.debate_generator is None:
            self.debate_generator = DebateGenerator.from_settings(self.settings)

    def build_match_debate(self, match_key: str, *, format: str = "chat") -> PunditDebateResponse:
        payload = load_replay_payload(self.session, match_key)
        analysis = analyze_match(payload)
        hot_takes = generate_hot_takes(analysis)
        lines = self.debate_generator.generate(analysis=analysis, hot_takes=hot_takes)
        return PunditDebateResponse(
            match_id=payload.match_id,
            headline=build_headline(analysis),
            format=format,
            analysis=PunditMatchAnalysisView(**analysis),
            personas=[PunditPersonaView(**persona) for persona in PUNDITS],
            hot_takes=hot_takes,
            lines=[
                PunditDebateLineView(
                    speaker=line.speaker,
                    style=line.style,
                    stance=line.stance,
                    line=line.line,
                    emphasis=line.emphasis,
                )
                for line in lines
            ],
            generated_at=datetime.now(UTC),
        )
