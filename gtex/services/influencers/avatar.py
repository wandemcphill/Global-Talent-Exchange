from __future__ import annotations

from dataclasses import asdict, dataclass

from services.influencers.personas import Persona


@dataclass(frozen=True, slots=True)
class AvatarSpec:
    render_mode: str
    image_prompt: str
    waveform_palette: tuple[str, str]
    layout: str
    provider_hint: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def build_avatar_spec(persona: Persona, *, talking_head: bool = False) -> AvatarSpec:
    if persona.name == "Coach Rage":
        palette = ("#8f1d1d", "#f4b400")
        image_prompt = "A furious touchline coach under floodlights with tactical boards and stadium smoke."
    elif persona.name == "Street Analyst":
        palette = ("#12711c", "#f2c94c")
        image_prompt = "A street football analyst with neon market lights, handheld mic, and animated crowd energy."
    else:
        palette = ("#123c69", "#dce7f2")
        image_prompt = "A composed tactical analyst in a studio with floating heatmaps and xG diagrams."
    return AvatarSpec(
        render_mode="talking_head" if talking_head else "static_waveform",
        image_prompt=image_prompt,
        waveform_palette=palette,
        layout="center_stage",
        provider_hint="d-id" if talking_head else "static-image-plus-waveform",
    )
