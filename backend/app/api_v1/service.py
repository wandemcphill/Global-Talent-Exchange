from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import os
from threading import RLock
from typing import Any
from uuid import uuid4

from fastapi import FastAPI

from app.models.user import User


class GlobalApiV1Error(ValueError):
    pass


class GlobalApiV1NotFoundError(GlobalApiV1Error):
    pass


class GlobalApiV1ValidationError(GlobalApiV1Error):
    pass


class GlobalApiV1RuntimeUnavailableError(GlobalApiV1Error):
    pass


@dataclass(slots=True)
class GlobalApiV1State:
    lock: RLock = field(default_factory=RLock)
    matches: dict[str, dict[str, Any]] = field(default_factory=dict)
    market_listings: dict[str, dict[str, Any]] = field(default_factory=dict)
    market_bids: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    regens: list[dict[str, Any]] = field(default_factory=list)
    competitions: list[dict[str, Any]] = field(default_factory=list)
    history_records: list[dict[str, Any]] = field(default_factory=list)
    clubs: dict[str, dict[str, Any]] = field(default_factory=dict)
    tournaments: dict[str, dict[str, Any]] = field(default_factory=dict)
    stories: list[dict[str, Any]] = field(default_factory=list)
    tasks: list[dict[str, Any]] = field(default_factory=list)
    task_claims: dict[str, set[str]] = field(default_factory=dict)
    follows: dict[str, set[str]] = field(default_factory=dict)
    user_profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    feed_items: list[dict[str, Any]] = field(default_factory=list)
    federations: dict[str, dict[str, Any]] = field(default_factory=dict)
    federation_members: dict[str, set[str]] = field(default_factory=dict)
    federation_votes: list[dict[str, Any]] = field(default_factory=list)
    broadcast_payments: set[tuple[str, str]] = field(default_factory=set)
    club_marketplace: dict[str, dict[str, Any]] = field(default_factory=dict)
    club_offers: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    notifications: dict[str, list[dict[str, Any]]] = field(default_factory=dict)


def _default_state() -> GlobalApiV1State:
    state = GlobalApiV1State()
    state.matches = {
        "m1": {
            "match_id": "m1",
            "status": "live",
            "teams": ["Lagos Titans", "FC Alpha"],
            "score": "2-1",
            "time": 72,
            "possession": [55, 45],
            "stats": {
                "shots": [10, 6],
                "xg": [1.8, 0.9],
            },
        },
        "m2": {
            "match_id": "m2",
            "status": "scheduled",
            "teams": ["Abuja Comets", "Kano Warriors"],
            "score": "0-0",
            "time": 0,
            "possession": [50, 50],
            "stats": {
                "shots": [0, 0],
                "xg": [0.0, 0.0],
            },
        },
    }
    state.market_listings = {
        "l1": {
            "listing_id": "l1",
            "player_id": "p1",
            "player_name": "Adeyemi Jr",
            "rating": 82,
            "position": "ST",
            "club": "Lagos Titans",
            "ask_price": 500000,
        },
        "l2": {
            "listing_id": "l2",
            "player_id": "p2",
            "player_name": "Santos Silva",
            "rating": 79,
            "position": "CM",
            "club": "FC Alpha",
            "ask_price": 420000,
        },
        "l3": {
            "listing_id": "l3",
            "player_id": "p3",
            "player_name": "Ibrahim Noor",
            "rating": 84,
            "position": "CB",
            "club": "Abuja Comets",
            "ask_price": 680000,
        },
    }
    state.market_bids = {"l1": [], "l2": [], "l3": []}
    state.regens = [
        {"id": "p1", "name": "Adeyemi Jr", "rating": 82, "potential": 92, "tags": ["hot", "wonderkid"]},
        {"id": "p2", "name": "Santos Silva", "rating": 79, "potential": 88, "tags": ["creative", "press_resistant"]},
        {"id": "p3", "name": "Ibrahim Noor", "rating": 84, "potential": 90, "tags": ["anchor", "leader"]},
    ]
    state.competitions = [
        {"id": "comp_1", "name": "West Africa Super League", "status": "live", "clubs": 20},
        {"id": "comp_2", "name": "Unity Cup", "status": "registration", "clubs": 8},
    ]
    state.history_records = [
        {"id": "rec_1", "title": "Longest unbeaten run", "holder": "Lagos Titans", "value": 18},
        {"id": "rec_2", "title": "Highest transfer fee", "holder": "FC Alpha", "value": 1200000},
    ]
    state.clubs = {
        "club_1": {
            "id": "club_1",
            "name": "Lagos Titans",
            "logo": "https://cdn.example.com/clubs/lagos-titans.png",
            "fan_sentiment": "happy",
            "league_position": 2,
            "country": "Nigeria",
            "stadium": "Atlantic Arena",
            "squad": [
                {"id": "p1", "name": "Adeyemi Jr", "position": "ST", "rating": 82},
                {"id": "p4", "name": "Kunle Bassey", "position": "RW", "rating": 80},
                {"id": "p5", "name": "Musa Bello", "position": "CB", "rating": 78},
            ],
            "finances": {
                "balance": 5200000,
                "wage_bill": 680000,
                "transfer_budget": 1450000,
            },
            "fans": {
                "total": 1850000,
                "sentiment": "happy",
                "engagement_score": 91,
            },
        },
        "club_2": {
            "id": "club_2",
            "name": "FC Alpha",
            "logo": "https://cdn.example.com/clubs/fc-alpha.png",
            "fan_sentiment": "tense",
            "league_position": 5,
            "country": "Nigeria",
            "stadium": "Summit Dome",
            "squad": [
                {"id": "p2", "name": "Santos Silva", "position": "CM", "rating": 79},
                {"id": "p6", "name": "Tari George", "position": "LB", "rating": 77},
            ],
            "finances": {
                "balance": 4100000,
                "wage_bill": 590000,
                "transfer_budget": 980000,
            },
            "fans": {
                "total": 1210000,
                "sentiment": "mixed",
                "engagement_score": 74,
            },
        },
    }
    state.tournaments = {
        "t1": {
            "id": "t1",
            "name": "Unity Cup",
            "status": "registration",
            "format": "8-team knockout",
            "entry_fee": 25000,
            "participants": set(),
            "rentals": [],
            "submitted_squads": {},
        }
    }
    state.stories = [
        {"id": "s1", "title": "Underdog Shock", "image": "https://cdn.example.com/stories/underdog.png", "type": "giant_killing"},
        {"id": "s2", "title": "Teenage Star Explodes", "image": "https://cdn.example.com/stories/teen-star.png", "type": "breakout"},
    ]
    state.tasks = [
        {"id": "task_daily_login", "title": "Daily Login", "reward": 100, "streak_target": 1},
        {"id": "task_watch_match", "title": "Watch a Live Match", "reward": 150, "streak_target": 3},
    ]
    state.user_profiles = {
        "creator_1": {
            "id": "creator_1",
            "display_name": "Scout Pulse",
            "bio": "Tracking the next global regen class.",
            "avatar": "https://cdn.example.com/users/scout-pulse.png",
        }
    }
    state.feed_items = [
        {"id": "feed_1", "type": "story", "title": "Underdog Shock", "summary": "Lagos Titans stunned the league leaders."},
        {"id": "feed_2", "type": "market", "title": "Wonderkid interest rising", "summary": "Three clubs are circling Adeyemi Jr."},
    ]
    state.federations = {
        "fed_1": {
            "id": "fed_1",
            "name": "West Africa Football Union",
            "region": "West Africa",
            "proposal_count": 2,
        }
    }
    state.federation_members = {"fed_1": set()}
    state.club_marketplace = {
        "club_listing_1": {
            "listing_id": "club_listing_1",
            "club_id": "club_2",
            "club_name": "FC Alpha",
            "asking_price": 32000000,
            "seller": "Board of FC Alpha",
            "note": "Seeking strategic investors.",
        }
    }
    state.club_offers = {"club_listing_1": []}
    return state


class GlobalApiV1Service:
    def __init__(self, app: FastAPI):
        self.app = app
        self._protected_environment = _is_protected_environment(app)
        self._demo_fixtures_enabled = _demo_fixtures_enabled(app)
        state = getattr(app.state, "global_api_v1_state", None)
        if state is None:
            state = _default_state() if self._demo_fixtures_enabled else GlobalApiV1State()
            app.state.global_api_v1_state = state
        self.state: GlobalApiV1State = state

    def build_dashboard(self, user: User) -> dict[str, Any]:
        if not self._demo_fixtures_enabled:
            return self._build_runtime_dashboard(user)
        self._ensure_profile(user)
        club = self._copy(self.state.clubs["club_1"])
        bids = self.state.market_bids.get("l1", [])
        return {
            "club": {
                "id": club["id"],
                "name": club["name"],
                "logo": club["logo"],
                "fan_sentiment": club["fan_sentiment"],
                "league_position": club["league_position"],
            },
            "quick_actions": [
                {"id": "qa_market", "label": "Scan transfer market", "route": "/market"},
                {"id": "qa_story", "label": "Open story engine", "route": "/stories"},
            ],
            "live_matches": [
                {
                    "match_id": item["match_id"],
                    "teams": item["teams"],
                    "score": item["score"],
                    "time": item["time"],
                }
                for item in self.state.matches.values()
                if item["status"] == "live"
            ],
            "stories": self._copy(self.state.stories[:3]),
            "tasks": self.list_tasks(user)["tasks"],
            "transfer_alerts": [
                {
                    "listing_id": bid["listing_id"],
                    "amount": bid["amount"],
                    "club": bid["club"],
                }
                for bid in bids[-3:]
            ],
            "trending_regens": self._copy(self.state.regens[:3]),
        }

    def get_match_state(self, match_id: str) -> dict[str, Any]:
        if not self._demo_fixtures_enabled:
            return self._build_runtime_match_state(match_id)
        return self._copy(self._get_match(match_id))

    def build_match_commentary_event(self, match_id: str) -> dict[str, Any]:
        if not self._demo_fixtures_enabled:
            return self._build_runtime_match_commentary_event(match_id)
        match = self._get_match(match_id)
        return {
            "type": "commentary",
            "text": f"{match['teams'][0]} keep the pressure on at minute {match['time']}.",
            "timestamp": match["time"],
        }

    def list_market_listings(self, *, page: int, rating_min: int | None, position: str | None) -> dict[str, Any]:
        if not self._demo_fixtures_enabled:
            return {"page": page, "total": 0, "listings": []}
        listings = [self._decorate_listing(item) for item in self.state.market_listings.values()]
        if rating_min is not None:
            listings = [item for item in listings if int(item["rating"]) >= rating_min]
        if position is not None:
            listings = [item for item in listings if str(item["position"]).upper() == position.upper()]
        page_size = 10
        start = (page - 1) * page_size
        end = start + page_size
        return {
            "page": page,
            "total": len(listings),
            "listings": self._copy(listings[start:end]),
        }

    def place_bid(self, user: User, *, listing_id: str, amount: int) -> dict[str, Any]:
        self._require_demo_fixture_support("market bidding")
        listing = self._get_listing(listing_id)
        if amount <= 0:
            raise GlobalApiV1ValidationError("Bid amount must be greater than zero.")
        bid = {
            "bid_id": f"bid_{uuid4().hex[:8]}",
            "listing_id": listing_id,
            "amount": amount,
            "club": self._club_name_for_user(user),
        }
        with self.state.lock:
            self.state.market_bids.setdefault(listing_id, []).append(bid)
            self._notify(
                user.id,
                {
                    "type": "new_bid",
                    "amount": amount,
                    "club": bid["club"],
                    "listing_id": listing_id,
                },
            )
        return {
            "bid": self._copy(bid),
            "listing": self._decorate_listing(listing),
        }

    def get_market_bid_event(self, listing_id: str) -> dict[str, Any]:
        self._require_demo_fixture_support("market bid streaming")
        self._get_listing(listing_id)
        bids = self.state.market_bids.get(listing_id, [])
        if bids:
            latest = bids[-1]
            return {
                "type": "new_bid",
                "amount": latest["amount"],
                "club": latest["club"],
            }
        listing = self._get_listing(listing_id)
        return {
            "type": "new_bid",
            "amount": listing["ask_price"],
            "club": listing["club"],
        }

    def list_regens(self) -> dict[str, Any]:
        if not self._demo_fixtures_enabled:
            return {"players": []}
        return {"players": self._copy(self.state.regens)}

    def list_competitions(self) -> dict[str, Any]:
        if not self._demo_fixtures_enabled:
            return {"competitions": []}
        return {"competitions": self._copy(self.state.competitions)}

    def list_history_records(self) -> dict[str, Any]:
        if not self._demo_fixtures_enabled:
            return {"records": []}
        return {"records": self._copy(self.state.history_records)}

    def list_federations(self) -> dict[str, Any]:
        return {
            "federations": [
                {
                    **self._copy(item),
                    "member_count": len(self.state.federation_members.get(federation_id, set())),
                }
                for federation_id, item in self.state.federations.items()
            ]
        }

    def get_player(self, player_id: str) -> dict[str, Any]:
        self._require_demo_fixture_support("player facade")
        player = next((item for item in self.state.regens if item["id"] == player_id), None)
        if player is None:
            raise GlobalApiV1NotFoundError(f"Player '{player_id}' was not found.")
        return {
            "id": player["id"],
            "name": player["name"],
            "rating": player["rating"],
            "attributes": {
                "pace": min(player["rating"] + 8, 99),
                "shooting": min(player["rating"] + 3, 99),
            },
            "story": self._copy(self.state.stories[:2]),
            "career": [
                {"season": "2026", "club": "Lagos Titans", "appearances": 21, "goals": 9},
            ],
            "offers": self._copy(self.state.market_bids.get("l1", [])),
        }

    def get_club(self, club_id: str) -> dict[str, Any]:
        self._require_demo_fixture_support("club facade")
        club = self._get_club(club_id)
        return {
            "id": club["id"],
            "name": club["name"],
            "logo": club["logo"],
            "country": club["country"],
            "stadium": club["stadium"],
            "league_position": club["league_position"],
            "fan_sentiment": club["fan_sentiment"],
        }

    def get_club_squad(self, club_id: str) -> dict[str, Any]:
        self._require_demo_fixture_support("club squad facade")
        club = self._get_club(club_id)
        return {"club_id": club_id, "players": self._copy(club["squad"])}

    def get_club_finances(self, club_id: str) -> dict[str, Any]:
        self._require_demo_fixture_support("club finance facade")
        club = self._get_club(club_id)
        return {"club_id": club_id, **self._copy(club["finances"])}

    def get_club_fans(self, club_id: str) -> dict[str, Any]:
        self._require_demo_fixture_support("club fan facade")
        club = self._get_club(club_id)
        return {"club_id": club_id, **self._copy(club["fans"])}

    def get_tournament(self, tournament_id: str) -> dict[str, Any]:
        self._require_demo_fixture_support("tournament facade")
        tournament = self._get_tournament(tournament_id)
        return {
            "id": tournament["id"],
            "name": tournament["name"],
            "status": tournament["status"],
            "format": tournament["format"],
            "entry_fee": tournament["entry_fee"],
            "participant_count": len(tournament["participants"]),
        }

    def join_tournament(self, user: User, tournament_id: str) -> dict[str, Any]:
        self._require_demo_fixture_support("tournament joins")
        tournament = self._get_tournament(tournament_id)
        with self.state.lock:
            tournament["participants"].add(user.id)
            self._notify(
                user.id,
                {
                    "type": "match_start",
                    "tournament_id": tournament_id,
                    "name": tournament["name"],
                },
            )
        return {
            "tournament_id": tournament_id,
            "user_id": user.id,
            "joined": True,
            "participant_count": len(tournament["participants"]),
        }

    def rent_player(self, user: User, *, tournament_id: str, player_id: str) -> dict[str, Any]:
        self._require_demo_fixture_support("tournament rentals")
        tournament = self._get_tournament(tournament_id)
        player = self.get_player(player_id)
        rental = {
            "rental_id": f"rent_{uuid4().hex[:8]}",
            "player_id": player["id"],
            "player_name": player["name"],
            "user_id": user.id,
        }
        with self.state.lock:
            tournament["rentals"].append(rental)
            self._notify(
                user.id,
                {
                    "type": "transfer_alert",
                    "player_id": player["id"],
                    "player_name": player["name"],
                },
            )
        return {
            "tournament_id": tournament_id,
            "rental": self._copy(rental),
        }

    def submit_squad(self, user: User, *, tournament_id: str, player_ids: list[str]) -> dict[str, Any]:
        self._require_demo_fixture_support("tournament squad submissions")
        tournament = self._get_tournament(tournament_id)
        with self.state.lock:
            tournament["submitted_squads"][user.id] = list(player_ids)
        return {
            "tournament_id": tournament_id,
            "user_id": user.id,
            "submitted": True,
            "player_ids": list(player_ids),
        }

    def get_broadcast(self, user: User, match_id: str) -> dict[str, Any]:
        self._require_demo_fixture_support("broadcast facade")
        match = self._get_match(match_id)
        return {
            "match_id": match_id,
            "teams": self._copy(match["teams"]),
            "price": 1000,
            "unlocked": (user.id, match_id) in self.state.broadcast_payments,
            "stream_status": "ready",
        }

    def pay_to_watch(self, user: User, *, match_id: str, amount: int | None) -> dict[str, Any]:
        self._require_demo_fixture_support("broadcast payments")
        self._get_match(match_id)
        with self.state.lock:
            self.state.broadcast_payments.add((user.id, match_id))
            self._notify(
                user.id,
                {
                    "type": "match_start",
                    "match_id": match_id,
                },
            )
        return {
            "match_id": match_id,
            "paid": True,
            "amount": amount if amount is not None else 1000,
        }

    def list_club_for_sale(self, user: User, *, club_id: str, asking_price: int | None, note: str | None) -> dict[str, Any]:
        self._require_demo_fixture_support("club sale listings")
        club = self._get_club(club_id)
        listing = {
            "listing_id": f"club_listing_{uuid4().hex[:8]}",
            "club_id": club_id,
            "club_name": club["name"],
            "asking_price": asking_price if asking_price is not None else 25000000,
            "seller": self._club_name_for_user(user),
            "note": note or "Club ownership opportunity.",
        }
        with self.state.lock:
            self.state.club_marketplace[listing["listing_id"]] = listing
            self.state.club_offers.setdefault(listing["listing_id"], [])
        return {"listing": self._copy(listing)}

    def get_club_marketplace(self) -> dict[str, Any]:
        if not self._demo_fixtures_enabled:
            return {"listings": []}
        listings = []
        for listing_id, item in self.state.club_marketplace.items():
            listing = self._copy(item)
            listing["offer_count"] = len(self.state.club_offers.get(listing_id, []))
            listings.append(listing)
        return {"listings": listings}

    def make_club_offer(self, user: User, *, listing_id: str, amount: int) -> dict[str, Any]:
        self._require_demo_fixture_support("club sale offers")
        listing = self.state.club_marketplace.get(listing_id)
        if listing is None:
            raise GlobalApiV1NotFoundError(f"Club listing '{listing_id}' was not found.")
        offer = {
            "offer_id": f"offer_{uuid4().hex[:8]}",
            "listing_id": listing_id,
            "amount": amount,
            "club": self._club_name_for_user(user),
        }
        with self.state.lock:
            self.state.club_offers.setdefault(listing_id, []).append(offer)
        return {"offer": self._copy(offer)}

    def get_user_profile(self, current_user: User, user_id: str) -> dict[str, Any]:
        self._require_demo_fixture_support("social profiles")
        if user_id == current_user.id:
            profile = self._ensure_profile(current_user)
        else:
            profile = self._get_or_create_synthetic_profile(user_id)
        followers = self._follower_count(user_id)
        following = len(self.state.follows.get(user_id, set()))
        return {
            "id": profile["id"],
            "display_name": profile["display_name"],
            "bio": profile["bio"],
            "avatar": profile["avatar"],
            "followers": followers,
            "following": following,
            "followed_by_current_user": user_id in self.state.follows.get(current_user.id, set()),
        }

    def follow_user(self, current_user: User, user_id: str) -> dict[str, Any]:
        self._require_demo_fixture_support("social follows")
        if user_id == current_user.id:
            raise GlobalApiV1ValidationError("Users cannot follow themselves.")
        self._get_or_create_synthetic_profile(user_id)
        with self.state.lock:
            self.state.follows.setdefault(current_user.id, set()).add(user_id)
        return {
            "user_id": user_id,
            "following": True,
            "followers": self._follower_count(user_id),
        }

    def get_feed(self, current_user: User) -> dict[str, Any]:
        if not self._demo_fixtures_enabled:
            return {"items": []}
        followed_ids = self.state.follows.get(current_user.id, set())
        items = self._copy(self.state.feed_items)
        if followed_ids:
            items.insert(
                0,
                {
                    "id": f"feed_follow_{next(iter(followed_ids))}",
                    "type": "social",
                    "title": "Network update",
                    "summary": "A followed manager has entered the market.",
                },
            )
        return {"items": items[:20]}

    def list_tasks(self, user: User) -> dict[str, Any]:
        if not self._demo_fixtures_enabled:
            return {"tasks": []}
        claimed = self.state.task_claims.get(user.id, set())
        return {
            "tasks": [
                {
                    **self._copy(task),
                    "claimed": task["id"] in claimed,
                }
                for task in self.state.tasks
            ]
        }

    def claim_task(self, user: User, task_id: str) -> dict[str, Any]:
        self._require_demo_fixture_support("task claiming")
        task = next((item for item in self.state.tasks if item["id"] == task_id), None)
        if task is None:
            raise GlobalApiV1NotFoundError(f"Task '{task_id}' was not found.")
        with self.state.lock:
            claimed = self.state.task_claims.setdefault(user.id, set())
            already_claimed = task_id in claimed
            claimed.add(task_id)
        return {
            "task_id": task_id,
            "claimed": True,
            "status": "already_claimed" if already_claimed else "claimed",
            "reward": 0 if already_claimed else task["reward"],
        }

    def get_stories(self) -> dict[str, Any]:
        if not self._demo_fixtures_enabled:
            return {"stories": []}
        return {"stories": self._copy(self.state.stories)}

    def generate_story(self, user: User, *, title: str | None, story_type: str, subject_id: str | None) -> dict[str, Any]:
        self._require_demo_fixture_support("story generation")
        story = {
            "id": f"s_{uuid4().hex[:8]}",
            "title": title or "Dynamic Storyline Triggered",
            "image": "https://cdn.example.com/stories/generated.png",
            "type": story_type,
            "subject_id": subject_id,
        }
        with self.state.lock:
            self.state.stories.insert(0, story)
            self.state.feed_items.insert(
                0,
                {
                    "id": f"feed_{uuid4().hex[:8]}",
                    "type": "story",
                    "title": story["title"],
                    "summary": f"Story engine generated a new {story_type} beat.",
                },
            )
            self._notify(
                user.id,
                {
                    "type": "story_event",
                    "story_id": story["id"],
                    "title": story["title"],
                },
            )
        return {"story": self._copy(story)}

    def create_federation(self, user: User, *, name: str, region: str | None) -> dict[str, Any]:
        self._require_demo_fixture_support("federation creation")
        federation_id = f"fed_{uuid4().hex[:8]}"
        federation = {
            "id": federation_id,
            "name": name,
            "region": region or "Global",
            "proposal_count": 0,
        }
        with self.state.lock:
            self.state.federations[federation_id] = federation
            self.state.federation_members[federation_id] = {user.id}
        return {
            "federation": {
                **self._copy(federation),
                "member_count": 1,
            }
        }

    def join_federation(self, user: User, federation_id: str) -> dict[str, Any]:
        self._require_demo_fixture_support("federation joins")
        self._get_federation(federation_id)
        with self.state.lock:
            members = self.state.federation_members.setdefault(federation_id, set())
            members.add(user.id)
        return {
            "federation_id": federation_id,
            "user_id": user.id,
            "joined": True,
            "member_count": len(self.state.federation_members.get(federation_id, set())),
        }

    def vote_federation(self, user: User, *, federation_id: str | None, proposal_id: str, vote: str) -> dict[str, Any]:
        self._require_demo_fixture_support("federation voting")
        resolved_federation_id = federation_id or next(iter(self.state.federations), None)
        if resolved_federation_id is None:
            raise GlobalApiV1NotFoundError("No federations are available for voting.")
        self._get_federation(resolved_federation_id)
        ballot = {
            "vote_id": f"vote_{uuid4().hex[:8]}",
            "federation_id": resolved_federation_id,
            "proposal_id": proposal_id,
            "vote": vote,
            "user_id": user.id,
        }
        with self.state.lock:
            self.state.federation_votes.append(ballot)
        return {"vote": self._copy(ballot)}

    def get_notification_event(self, user_id: str) -> dict[str, Any]:
        if not self._demo_fixtures_enabled:
            return {
                "type": "notification",
                "title": "No new notifications.",
            }
        items = self.state.notifications.get(user_id, [])
        if items:
            return self._copy(items[-1])
        return {
            "type": "match_start",
            "match_id": "m1",
            "title": "Lagos Titans vs FC Alpha is live.",
        }

    def _get_match(self, match_id: str) -> dict[str, Any]:
        match = self.state.matches.get(match_id)
        if match is None:
            raise GlobalApiV1NotFoundError(f"Match '{match_id}' was not found.")
        return match

    def _build_runtime_dashboard(self, user: User) -> dict[str, Any]:
        live_matches = []
        hub = getattr(self.app.state, "live_match_hub", None)
        if hub is not None:
            for match_id in hub.list_active_matches()[:10]:
                try:
                    state = hub.get_state(match_id)
                    playback = hub.get_playback_context(match_id)
                except Exception:
                    continue
                if state is None:
                    continue
                home_name = (
                    playback.viewer_state.home_team.team_name
                    if playback is not None and playback.viewer_state is not None
                    else "Home"
                )
                away_name = (
                    playback.viewer_state.away_team.team_name
                    if playback is not None and playback.viewer_state is not None
                    else "Away"
                )
                live_matches.append(
                    {
                        "match_id": match_id,
                        "teams": [home_name, away_name],
                        "score": f"{state.snapshot.score.home}-{state.snapshot.score.away}",
                        "time": state.snapshot.current_minute,
                    }
                )
        return {
            "club": {
                "id": getattr(user, "active_organization_id", None) or user.id,
                "name": getattr(user, "active_organization_name", None) or self._club_name_for_user(user),
                "logo": None,
                "fan_sentiment": None,
                "league_position": None,
            },
            "quick_actions": [],
            "live_matches": live_matches,
            "stories": [],
            "tasks": [],
            "transfer_alerts": [],
            "trending_regens": [],
        }

    def _build_runtime_match_state(self, match_id: str) -> dict[str, Any]:
        hub = getattr(self.app.state, "live_match_hub", None)
        if hub is None:
            raise GlobalApiV1NotFoundError(f"Match '{match_id}' was not found.")
        state = hub.get_state(match_id)
        playback = hub.get_playback_context(match_id)
        if state is None:
            raise GlobalApiV1NotFoundError(f"Match '{match_id}' was not found.")
        home_name = (
            playback.viewer_state.home_team.team_name
            if playback is not None and playback.viewer_state is not None
            else "Home"
        )
        away_name = (
            playback.viewer_state.away_team.team_name
            if playback is not None and playback.viewer_state is not None
            else "Away"
        )
        return {
            "match_id": match_id,
            "status": state.snapshot.status,
            "teams": [home_name, away_name],
            "score": f"{state.snapshot.score.home}-{state.snapshot.score.away}",
            "time": state.snapshot.current_minute,
            "possession": [state.snapshot.possession_estimate.home, state.snapshot.possession_estimate.away],
            "stats": {
                "spectator_count": state.spectator_count,
                "event_count": state.event_count,
            },
        }

    def _build_runtime_match_commentary_event(self, match_id: str) -> dict[str, Any]:
        hub = getattr(self.app.state, "live_match_hub", None)
        if hub is None:
            raise GlobalApiV1NotFoundError(f"Match '{match_id}' was not found.")
        events, _cursor = hub.get_events_since(match_id, 0)
        if not events:
            state = hub.get_state(match_id)
            if state is None:
                raise GlobalApiV1NotFoundError(f"Match '{match_id}' was not found.")
            return {
                "type": "commentary",
                "text": f"Live coverage ready at minute {state.snapshot.current_minute}.",
                "timestamp": state.snapshot.current_minute,
            }
        latest = events[-1]
        return {
            "type": "commentary",
            "text": latest.commentary or latest.event_type.replace("_", " ").title(),
            "timestamp": latest.minute,
        }

    def _require_demo_fixture_support(self, operation: str) -> None:
        if self._demo_fixtures_enabled:
            return
        raise GlobalApiV1RuntimeUnavailableError(
            f"{operation.capitalize()} is unavailable because the protected-environment API v1 demo fixtures are disabled."
        )

    def _get_listing(self, listing_id: str) -> dict[str, Any]:
        listing = self.state.market_listings.get(listing_id)
        if listing is None:
            raise GlobalApiV1NotFoundError(f"Listing '{listing_id}' was not found.")
        return listing

    def _get_club(self, club_id: str) -> dict[str, Any]:
        club = self.state.clubs.get(club_id)
        if club is None:
            raise GlobalApiV1NotFoundError(f"Club '{club_id}' was not found.")
        return club

    def _get_tournament(self, tournament_id: str) -> dict[str, Any]:
        tournament = self.state.tournaments.get(tournament_id)
        if tournament is None:
            raise GlobalApiV1NotFoundError(f"Tournament '{tournament_id}' was not found.")
        return tournament

    def _get_federation(self, federation_id: str) -> dict[str, Any]:
        federation = self.state.federations.get(federation_id)
        if federation is None:
            raise GlobalApiV1NotFoundError(f"Federation '{federation_id}' was not found.")
        return federation

    def _decorate_listing(self, listing: dict[str, Any]) -> dict[str, Any]:
        payload = self._copy(listing)
        bids = self.state.market_bids.get(str(listing["listing_id"]), [])
        payload["latest_bid"] = self._copy(bids[-1]) if bids else None
        return payload

    def _ensure_profile(self, user: User) -> dict[str, Any]:
        profile = self.state.user_profiles.get(user.id)
        if profile is None:
            profile = {
                "id": user.id,
                "display_name": user.display_name or user.full_name or user.username,
                "bio": "Global Talent Exchange manager profile.",
                "avatar": None,
            }
            self.state.user_profiles[user.id] = profile
        return profile

    def _get_or_create_synthetic_profile(self, user_id: str) -> dict[str, Any]:
        profile = self.state.user_profiles.get(user_id)
        if profile is None:
            profile = {
                "id": user_id,
                "display_name": f"Manager {user_id[-4:]}",
                "bio": "Synthetic profile served by the v1 facade.",
                "avatar": None,
            }
            self.state.user_profiles[user_id] = profile
        return profile

    def _follower_count(self, user_id: str) -> int:
        return sum(1 for follows in self.state.follows.values() if user_id in follows)

    def _club_name_for_user(self, user: User) -> str:
        return user.display_name or user.full_name or user.username

    def _notify(self, user_id: str, payload: dict[str, Any]) -> None:
        stream = self.state.notifications.setdefault(user_id, [])
        stream.append(deepcopy(payload))
        if len(stream) > 20:
            del stream[:-20]

    @staticmethod
    def _copy(payload: Any) -> Any:
        return deepcopy(payload)


def _is_protected_environment(app: FastAPI) -> bool:
    settings = getattr(app.state, "settings", None)
    environment = str(getattr(settings, "app_env", "") or "").strip().lower()
    return environment in {"production", "prod", "staging"}


def _demo_fixtures_enabled(app: FastAPI) -> bool:
    if not _is_protected_environment(app):
        return True
    return str(os.getenv("GTE_ENABLE_API_V1_DEMO_FIXTURES", "")).strip().lower() in {"1", "true", "yes", "on"}
