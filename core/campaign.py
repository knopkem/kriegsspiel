"""Campaign mode — links multiple scenarios into a sequential campaign.

A campaign is a list of :class:`CampaignScenario` entries played in order.
After each battle the :class:`CampaignState` records the result and carries a
fraction of surviving units' HP into the next scenario.

Persistence uses a simple JSON file so campaigns survive app restarts.

Example usage::

    from core.campaign import STANDARD_CAMPAIGN, CampaignState
    state = CampaignState(campaign=STANDARD_CAMPAIGN)
    # After a battle finishes:
    state.record_result("skirmish_small", winner=Side.BLUE, surviving_units=game.units)
    state.save("campaign_save.json")
    # Load later:
    state = CampaignState.load("campaign_save.json", STANDARD_CAMPAIGN)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .units import Side, Unit


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CampaignScenario:
    """One battle in a campaign."""

    scenario_id: str
    title: str
    description: str
    hp_carry_fraction: float = 0.75   # fraction of remaining HP carried to next scenario
    required_to_advance: bool = True  # must win to proceed to next scenario


@dataclass
class BattleResult:
    """Recorded outcome of a single campaign battle."""

    scenario_id: str
    winner: Side | None      # None = draw / no winner
    turns_taken: int
    blue_units_surviving: int
    red_units_surviving: int


@dataclass
class CampaignState:
    """Tracks progress through a campaign."""

    campaign: list[CampaignScenario]
    results: list[BattleResult] = field(default_factory=list)
    # Carry-over HP ratios keyed by unit_id (from previous battle)
    unit_hp_carry: dict[str, float] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def current_scenario_index(self) -> int:
        """Index of the next unplayed scenario."""
        return len(self.results)

    @property
    def current_scenario(self) -> CampaignScenario | None:
        idx = self.current_scenario_index
        if idx >= len(self.campaign):
            return None
        return self.campaign[idx]

    @property
    def is_complete(self) -> bool:
        return self.current_scenario_index >= len(self.campaign)

    @property
    def blue_wins(self) -> int:
        return sum(1 for r in self.results if r.winner is Side.BLUE)

    @property
    def red_wins(self) -> int:
        return sum(1 for r in self.results if r.winner is Side.RED)

    @property
    def campaign_winner(self) -> Side | None:
        """Return the campaign winner once complete, or None if still playing."""
        if not self.is_complete:
            return None
        if self.blue_wins > self.red_wins:
            return Side.BLUE
        if self.red_wins > self.blue_wins:
            return Side.RED
        return None  # draw

    def scenario_result(self, scenario_id: str) -> BattleResult | None:
        for r in self.results:
            if r.scenario_id == scenario_id:
                return r
        return None

    # ------------------------------------------------------------------
    # Recording results
    # ------------------------------------------------------------------

    def record_result(
        self,
        scenario_id: str,
        *,
        winner: Side | None,
        turns_taken: int,
        surviving_units: Iterable[Unit],
    ) -> None:
        """Record a completed battle and update carry-over HP."""
        units = list(surviving_units)
        blues = [u for u in units if u.side is Side.BLUE and not u.is_removed]
        reds  = [u for u in units if u.side is Side.RED  and not u.is_removed]

        self.results.append(BattleResult(
            scenario_id=scenario_id,
            winner=winner,
            turns_taken=turns_taken,
            blue_units_surviving=len(blues),
            red_units_surviving=len(reds),
        ))

        # Store carry-over HP ratios for surviving player (BLUE) units
        carry = {}
        current = next(
            (scenario for scenario in self.campaign if scenario.scenario_id == scenario_id),
            None,
        )
        carry_fraction = current.hp_carry_fraction if current is not None else 1.0
        for u in blues:
            if u.max_hit_points > 0:
                ratio = (u.hit_points / u.max_hit_points) * carry_fraction
                carry[u.id] = max(0.1, ratio)   # keep at least 10% HP
        self.unit_hp_carry = carry

    def apply_carry_over(self, units: dict[str, Unit]) -> None:
        """Apply carry-over HP fractions to units at the start of a new battle."""
        for unit_id, ratio in self.unit_hp_carry.items():
            if unit_id in units:
                u = units[unit_id]
                u.hit_points = max(1, int(u.max_hit_points * ratio))

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        data = {
            "results": [
                {
                    "scenario_id": r.scenario_id,
                    "winner": r.winner.value if r.winner else None,
                    "turns_taken": r.turns_taken,
                    "blue_units_surviving": r.blue_units_surviving,
                    "red_units_surviving": r.red_units_surviving,
                }
                for r in self.results
            ],
            "unit_hp_carry": self.unit_hp_carry,
        }
        Path(path).write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: str, campaign: list[CampaignScenario]) -> "CampaignState":
        data = json.loads(Path(path).read_text())
        results = [
            BattleResult(
                scenario_id=r["scenario_id"],
                winner=Side(r["winner"]) if r["winner"] else None,
                turns_taken=r["turns_taken"],
                blue_units_surviving=r["blue_units_surviving"],
                red_units_surviving=r["red_units_surviving"],
            )
            for r in data.get("results", [])
        ]
        results = results[:len(campaign)]
        return cls(
            campaign=campaign,
            results=results,
            unit_hp_carry=data.get("unit_hp_carry", {}),
        )

    def summary(self) -> str:
        """Human-readable campaign progress string."""
        lines = [f"Campaign: {self.blue_wins}W / {self.red_wins}L / {len(self.results) - self.blue_wins - self.red_wins}D"]
        for i, scen in enumerate(self.campaign):
            r = self.scenario_result(scen.scenario_id)
            if r is None:
                status = "[ ] Upcoming"
            elif r.winner is Side.BLUE:
                status = "[✓] Victory"
            elif r.winner is Side.RED:
                status = "[✗] Defeat"
            else:
                status = "[=] Draw"
            lines.append(f"  {i+1}. {scen.title:30s} {status}")
        if self.is_complete:
            winner = self.campaign_winner
            lines.append(f"\nCampaign over — {'BLUE wins!' if winner is Side.BLUE else 'RED wins!' if winner else 'Draw'}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Built-in campaign definitions
# ---------------------------------------------------------------------------

STANDARD_CAMPAIGN: list[CampaignScenario] = [
    CampaignScenario(
        scenario_id="tutorial",
        title="Drill Day",
        description="Learn the basics of command before the real campaign begins.",
        hp_carry_fraction=0.9,
        required_to_advance=False,
    ),
    CampaignScenario(
        scenario_id="skirmish_small",
        title="First Blood",
        description="A skirmish at a river crossing — seize the crossing before the enemy does.",
        hp_carry_fraction=0.8,
    ),
    CampaignScenario(
        scenario_id="assault_on_hill",
        title="Assault on the Hill",
        description="Storm the fortified ridge position before enemy reinforcements arrive.",
        hp_carry_fraction=0.75,
    ),
    CampaignScenario(
        scenario_id="full_battle",
        title="Decisive Engagement",
        description="A full-scale pitched battle — all forces committed. Secure the field.",
        hp_carry_fraction=0.7,
    ),
]

HISTORICAL_CAMPAIGN: list[CampaignScenario] = [
    CampaignScenario(
        scenario_id="mockern_1813",
        title="Möckern (1813)",
        description="Force the crossing of the Elster and seize Möckern from French defenders.",
        hp_carry_fraction=0.75,
    ),
    CampaignScenario(
        scenario_id="ligny_1815",
        title="Ligny (1815)",
        description="Hold the Ligny stream against Napoleon's assault. Every hour matters.",
        hp_carry_fraction=0.7,
    ),
]
