"""Probabilistic belief tracking for enemy unit positions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.fog_of_war import VisibilitySnapshot
    from core.map import HexCoord


@dataclass
class EnemyBelief:
    unit_id: str
    unit_name: str
    last_known_pos: "HexCoord"
    last_seen_turn: int
    estimated_pos: "HexCoord"
    confidence: float = 1.0  # 1.0 = just seen, decays each turn


@dataclass
class BeliefMap:
    """Maintains estimated enemy positions based on sightings and projection."""

    beliefs: dict[str, EnemyBelief] = field(default_factory=dict)

    def update(self, visibility: "VisibilitySnapshot", current_turn: int) -> None:
        """Update beliefs from current visibility snapshot."""
        for unit_id, sighting in visibility.last_known_enemies.items():
            if unit_id in visibility.visible_enemy_units:
                # Currently visible — full confidence, exact position known
                self.beliefs[unit_id] = EnemyBelief(
                    unit_id=unit_id,
                    unit_name=unit_id,
                    last_known_pos=sighting.position,
                    last_seen_turn=sighting.seen_on_turn,
                    estimated_pos=sighting.position,
                    confidence=1.0,
                )
            elif unit_id in self.beliefs:
                # Known but not currently visible — decay confidence, project position
                belief = self.beliefs[unit_id]
                turns_ago = current_turn - sighting.seen_on_turn
                dq = sighting.position.q - belief.last_known_pos.q
                dr = sighting.position.r - belief.last_known_pos.r
                from core.map import HexCoord
                self.beliefs[unit_id] = EnemyBelief(
                    unit_id=unit_id,
                    unit_name=belief.unit_name,
                    last_known_pos=sighting.position,
                    last_seen_turn=sighting.seen_on_turn,
                    estimated_pos=HexCoord(sighting.position.q + dq, sighting.position.r + dr),
                    confidence=max(0.1, 1.0 - turns_ago * 0.15),
                )
            else:
                # New sighting
                self.beliefs[unit_id] = EnemyBelief(
                    unit_id=unit_id,
                    unit_name=unit_id,
                    last_known_pos=sighting.position,
                    last_seen_turn=sighting.seen_on_turn,
                    estimated_pos=sighting.position,
                    confidence=max(0.1, 1.0 - (current_turn - sighting.seen_on_turn) * 0.15),
                )

        # Remove beliefs for units no longer in any sighting
        known_ids = set(visibility.last_known_enemies.keys()) | set(visibility.visible_enemy_units)
        stale = [uid for uid in self.beliefs if uid not in known_ids]
        for uid in stale:
            del self.beliefs[uid]

    def estimated_enemies(self, min_confidence: float = 0.0) -> list[EnemyBelief]:
        """Return all enemy beliefs above confidence threshold, sorted by confidence."""
        return sorted(
            [b for b in self.beliefs.values() if b.confidence >= min_confidence],
            key=lambda b: b.confidence,
            reverse=True,
        )
