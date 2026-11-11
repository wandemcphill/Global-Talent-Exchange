"""Autoplay inspection frames for physical luxury showroom items."""

from __future__ import annotations

PREFIX = "/assets/showroom/inspection"


def _frame(label: str, kind: str, filename: str) -> dict[str, str]:
    return {"label": label, "kind": kind, "src": f"{PREFIX}/{filename}"}


SHOWROOM_INSPECTION_REELS: dict[str, list[dict[str, str]]] = {
    "sovereign_900x_jet": [
        _frame("Body", "image", "gtex-lux-jet-body.jpg"),
        _frame("Engine", "image", "gtex-lux-jet-engine.jpg"),
        _frame("Cockpit", "image", "gtex-lux-jet-cockpit.jpg"),
        _frame("Cabin seats", "image", "gtex-lux-jet-seats.jpg"),
        _frame("Lavatory", "image", "gtex-lux-jet-lavatory.jpg"),
        _frame("Galley", "image", "gtex-lux-jet-galley.jpg"),
        _frame("Cabin walk", "video", "gtex-lux-jet-cabin-walk.mp4"),
        _frame("Cockpit walk", "video", "gtex-lux-jet-cockpit-walk.mp4"),
        _frame("Lavatory walk", "video", "gtex-lux-jet-lavatory-walk.mp4"),
        _frame("360 turn", "video", "gtex-lux-jet-360.mp4"),
    ],
    "gulfstream_g700_exec_jet": [
        _frame("Body", "image", "gtex-lux-flagship-body.jpg"),
        _frame("Cockpit", "image", "gtex-lux-flagship-cockpit.jpg"),
        _frame("Club suite", "image", "gtex-lux-flagship-suite.jpg"),
        _frame("Suite walk", "video", "gtex-lux-flagship-suite-walk.mp4"),
        _frame("360 turn", "video", "gtex-lux-flagship-360.mp4"),
    ],
    "veloce_gt9_hypercar": [
        _frame("Body", "image", "gtex-lux-hypercar-body.jpg"),
        _frame("Rear", "image", "gtex-lux-hypercar-rear.jpg"),
        _frame("Cabin", "image", "gtex-lux-hypercar-interior.jpg"),
        _frame("Engine", "image", "gtex-lux-hypercar-engine.jpg"),
        _frame("Cabin walk", "video", "gtex-lux-hypercar-cabin-walk.mp4"),
        _frame("360 turn", "video", "gtex-lux-hypercar-360.mp4"),
    ],
    "executive_suv_command": [
        _frame("Body", "image", "gtex-lux-suv-body.jpg"),
        _frame("Rear lounge", "image", "gtex-lux-suv-lounge.jpg"),
        _frame("Lounge walk", "video", "gtex-lux-suv-lounge-walk.mp4"),
        _frame("360 turn", "video", "gtex-lux-suv-360.mp4"),
    ],
    "vanguard_xii_coach": [
        _frame("Body", "image", "gtex-lux-coach-body.jpg"),
        _frame("Cabin", "image", "gtex-lux-coach-cabin.jpg"),
        _frame("Cabin walk", "video", "gtex-lux-coach-cabin-walk.mp4"),
        _frame("360 turn", "video", "gtex-lux-coach-360.mp4"),
    ],
    "chronos_tourbillon_watch": [
        _frame("Dial", "image", "gtex-lux-watch-dial.jpg"),
        _frame("Movement", "image", "gtex-lux-watch-movement.jpg"),
        _frame("360 turn", "video", "gtex-lux-watch-360.mp4"),
    ],
    "superyacht": [
        _frame("Hull", "image", "gtex-lux-yacht-body.jpg"),
        _frame("Salon", "image", "gtex-lux-yacht-salon.jpg"),
        _frame("Owner cabin", "image", "gtex-lux-yacht-cabin.jpg"),
        _frame("Bridge", "image", "gtex-lux-yacht-bridge.jpg"),
        _frame("Salon walk", "video", "gtex-lux-yacht-salon-walk.mp4"),
        _frame("Cabin walk", "video", "gtex-lux-yacht-cabin-walk.mp4"),
        _frame("360 turn", "video", "gtex-lux-yacht-360.mp4"),
    ],
    "penthouse_box_suite": [
        _frame("Box", "image", "gtex-lux-penthouse-box.jpg"),
        _frame("Dining room", "image", "gtex-lux-penthouse-dining.jpg"),
        _frame("Lounge", "image", "gtex-lux-penthouse-lounge.jpg"),
        _frame("Dining walk", "video", "gtex-lux-penthouse-dining-walk.mp4"),
        _frame("Lounge walk", "video", "gtex-lux-penthouse-lounge-walk.mp4"),
        _frame("360 turn", "video", "gtex-lux-penthouse-360.mp4"),
    ],
    "high_performance_recovery_wing": [
        _frame("Wing", "image", "gtex-lux-cryo-wing.jpg"),
        _frame("Hydrotherapy", "image", "gtex-lux-cryo-pool.jpg"),
        _frame("Cryo chambers", "image", "gtex-lux-cryo-chamber.jpg"),
        _frame("Biomechanics lab", "image", "gtex-lux-cryo-lab.jpg"),
        _frame("Pool walk", "video", "gtex-lux-cryo-pool-walk.mp4"),
        _frame("Cryo walk", "video", "gtex-lux-cryo-chamber-walk.mp4"),
        _frame("Lab walk", "video", "gtex-lux-cryo-lab-walk.mp4"),
        _frame("360 turn", "video", "gtex-lux-cryo-360.mp4"),
    ],
    "elite_academy_boarding_wing": [
        _frame("Pavilion", "image", "gtex-lux-academy-pavilion.jpg"),
        _frame("Scholar suite", "image", "gtex-lux-academy-suite.jpg"),
        _frame("Classroom", "image", "gtex-lux-academy-classroom.jpg"),
        _frame("Pitch walk", "video", "gtex-lux-academy-pitch-walk.mp4"),
        _frame("Suite walk", "video", "gtex-lux-academy-suite-walk.mp4"),
        _frame("Classroom walk", "video", "gtex-lux-academy-classroom-walk.mp4"),
        _frame("360 turn", "video", "gtex-lux-academy-360.mp4"),
    ],
}


def inspection_reel(catalog_key: str) -> list[dict[str, str]]:
    return list(SHOWROOM_INSPECTION_REELS.get(catalog_key, ()))
