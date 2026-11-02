from __future__ import annotations

from app.players.gsi_service import (
    CANONICAL_GSI_OVERRIDES,
    PROVIDER_ID_GSI_OVERRIDES,
    resolve_player_gsi,
)


class DummyPlayer:
    def __init__(
        self,
        full_name: str,
        canonical_display_name: str | None = None,
        provider_external_id: str | None = None,
        position: str = "MF",
        governed_gsi: int | None = None,
        governed_potential_gsi: int | None = None,
        real_player_tier: str = "wonderkid",
        dna_profile: dict | None = None,
    ):
        self.full_name = full_name
        self.canonical_display_name = canonical_display_name or full_name
        self.provider_external_id = provider_external_id
        self.position = position
        self.governed_gsi = governed_gsi
        self.governed_potential_gsi = governed_potential_gsi
        self.real_player_tier = real_player_tier
        self.dna_profile = dna_profile or {}


def test_marc_bernal_calibration() -> None:
    # 1. Canonical override check
    assert CANONICAL_GSI_OVERRIDES["marc bernal"] == (77, 89)
    assert CANONICAL_GSI_OVERRIDES["marc bernal casas"] == (77, 89)
    assert PROVIDER_ID_GSI_OVERRIDES["2002042937"] == (77, 89)

    # 2. Player object resolution with governed attributes
    bernal = DummyPlayer(
        full_name="Marc Bernal",
        canonical_display_name="Marc Bernal",
        provider_external_id="2002042937",
        position="DM/CM",
        governed_gsi=77,
        governed_potential_gsi=89,
        dna_profile={"current_rating": 77, "overall": 77, "potential": 89},
    )
    cur, pot = resolve_player_gsi(bernal)
    assert cur == 77
    assert pot == 89
    assert bernal.position == "DM/CM"


def test_wonderkids_canonical_and_provider_overrides() -> None:
    expected_benchmarks = {
        "ethan nwaneri": (78, 90),
        "ayyoub bouaddi": (77, 89),
        "archie gray": (77, 88),
        "kobbie mainoo": (81, 91),
        "estêvão": (81, 91),
        "franco mastantuono": (78, 90),
        "kendry páez": (77, 89),
        "chris rigg": (74, 88),
        "mikey moore": (75, 90),
        "max dowman": (74, 89),
        "jj gabriel": (73, 92),
        "francesco camarda": (77, 91),
        "myles lewis-skelly": (76, 88),
        "rio ngumoha": (75, 89),
        "sverre nypan": (76, 89),
        "jorrel hato": (81, 89),
        "lucas bergvall": (78, 89),
        "aleksandar pavlović": (82, 89),
        "kenan yıldız": (84, 91),
        "leny yoro": (81, 90),
        "paul wanner": (77, 88),
        "can uzun": (77, 89),
        "geovany quenda": (77, 89),
        "rodrigo mora": (75, 88),
        "pau cubarsí": (83, 92),
        "dean huijsen": (78, 88),
        "lewis miley": (76, 88),
        "ebrima tunkara": (73, 90),
        "guille fernández": (77, 89),
        "toni fernández": (77, 89),
        "cavan sullivan": (76, 90),
        "finlay gorman": (74, 89),
        "amara diouf": (76, 90),
        "luka vušković": (77, 89),
        "konstantinos karetsas": (76, 88),
        "shumaira mheuka": (77, 88),
        "chido obi": (75, 89),
        "saba kharebashvili": (74, 88),
        "gabriel mec": (78, 89),
        "endrick": (81, 91),
        "arda güler": (82, 90),
        "warren zaïre-emery": (83, 90),
        "assan ouédraogo": (77, 88),
        "michal zuk": (73, 87),
        "shane kluivert": (72, 86),
        "ruslan mba": (73, 87),
        "pedro rodríguez": (73, 87),
        "justin lerma": (74, 88),
        "enzo alves": (73, 88),
        "claudio echeverri": (78, 89),
        "mathys tel": (80, 89),
        "samu omorodion": (81, 89),
        "lennart karl": (78, 91),
        "ethan mbappé": (72, 85),
        "amir ibragimov": (76, 88),
        "cardoso varela": (77, 89),
        "sean steur": (73, 87),
        "andrea natali": (74, 86),
    }

    for name, expected in expected_benchmarks.items():
        assert name in CANONICAL_GSI_OVERRIDES, f"Missing canonical override for {name}"
        assert (
            CANONICAL_GSI_OVERRIDES[name] == expected
        ), f"Mismatch for {name}: expected {expected}, got {CANONICAL_GSI_OVERRIDES[name]}"

        # Test resolve_player_gsi without explicit governed columns falls back to canonical override
        player = DummyPlayer(full_name=name)
        cur, pot = resolve_player_gsi(player)
        assert (cur, pot) == expected, f"Resolution failed for {name}"
