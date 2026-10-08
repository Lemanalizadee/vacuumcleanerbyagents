"""
Three agent programs from the course slides:

  1. Simple reflex agent  - condition-action rules, looks only at the CURRENT percept
  2. Goal-based agent     - has a model of the world + an explicit goal, plans ahead (BFS)
  3. Utility-based agent  - compares alternatives with a utility function U(state)
                            and balances reward against cost and battery

Every agent implements   act(percept) -> (action, explanation)
"""
from __future__ import annotations

import random
from typing import List, Optional, Tuple

from .environment import REWARD_PER_UNIT, Percept, bfs, path_actions


class SimpleReflexAgent:
    id = "simple_reflex"
    name = "Simple reflex agent"
    description = (
        "Condition-action rules on the current percept only. No memory, no map, no planning: "
        "if dirty -> SUCK, else wander in a random free direction."
    )

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)

    def act(self, p: Percept) -> Tuple[str, str]:
        # uses ONLY p.dirty and p.blocked (local sensors)
        if p.dirty:
            return "SUCK", "Rule 1: square is dirty -> SUCK"
        free = [a for a, is_blocked in p.blocked.items() if not is_blocked]
        if not free:
            return "NOOP", "Boxed in by obstacles - no rule applies"
        action = self.rng.choice(free)
        return action, f"Rule 2: square is clean -> move {action} (random free direction)"


class GoalBasedAgent:
    id = "goal_based"
    name = "Goal-based agent"
    description = (
        "Knows the map and has the explicit goal 'no dirt left'. It searches (BFS) for the "
        "shortest path to the nearest dirt and follows that plan. It does not watch its battery."
    )

    def __init__(self, seed: Optional[int] = None):
        self.plan: List[str] = []
        self.target = None

    def act(self, p: Percept) -> Tuple[str, str]:
        w = p.world
        if not w.dirt:
            return "NOOP", "Goal reached: room is clean"
        if p.dirty:
            self.plan, self.target = [], None
            return "SUCK", "Reached the target square -> SUCK"
        if not self.plan or self.target not in w.dirt:
            dist, parent = bfs(w, p.pos)
            reachable = [d for d in w.dirt if d in dist]
            if not reachable:
                return "NOOP", "Remaining dirt is unreachable"
            self.target = min(reachable, key=lambda d: (dist[d], d))
            self.plan = path_actions(parent, p.pos, self.target)
            why = f"New plan: nearest dirt is {self.target}, {len(self.plan)} steps away"
        else:
            why = f"Following plan to {self.target} ({len(self.plan)} steps left)"
        return self.plan.pop(0), why


class UtilityBasedAgent:
    id = "utility_based"
    name = "Utility-based agent"
    description = (
        "Scores every dirt square with a utility U = reward / cost, so big dirt that is close "
        "beats small dirt that is far. It only accepts a target if it can still get back to the "
        "charger, and goes to CHARGE when no target is safe."
    )

    def __init__(self, seed: Optional[int] = None):
        self.plan: List[str] = []
        self.target = None

    def act(self, p: Percept) -> Tuple[str, str]:
        w = p.world
        if not w.dirt:
            return "NOOP", "Room is clean"
        if p.dirty:
            self.plan, self.target = [], None
            return "SUCK", f"Cleaning here: +{REWARD_PER_UNIT * p.dirty} reward"

        if self.plan and self.target in w.dirt:
            return self.plan.pop(0), f"Following plan to {self.target} (battery {p.battery})"

        dist, parent = bfs(w, p.pos)
        home, _ = bfs(w, w.start)  # distance from every square to the charger (grid is symmetric)

        best = None  # (utility, cell, distance)
        for cell, amount in w.dirt.items():
            if cell not in dist or cell not in home:
                continue
            d = dist[cell]
            battery_needed = d + 1 + home[cell]  # walk there + suck + walk back to charger
            if battery_needed > p.battery:
                continue  # not safe -> utility is effectively -infinity
            utility = REWARD_PER_UNIT * amount / (d + 1)
            if best is None or utility > best[0]:
                best = (utility, cell, d)

        if best:
            utility, cell, d = best
            self.target = cell
            self.plan = path_actions(parent, p.pos, cell)
            amount = w.dirt[cell]
            why = f"Best utility U={utility:.1f} -> {cell} (dirt x{amount}, {d} steps)"
            return self.plan.pop(0), why

        # nothing safe to clean from here
        if p.pos == w.start:
            if p.battery < p.battery_max:
                return "CHARGE", "No safe target with this battery -> CHARGE"
            return "NOOP", "Even with a full battery the remaining dirt is out of range"
        if w.start in dist:
            self.target = None
            self.plan = path_actions(parent, p.pos, w.start)
            return self.plan.pop(0), "Battery too low for any target -> heading to the charger"
        return "NOOP", "Cannot reach the charger"


AGENTS = {cls.id: cls for cls in (SimpleReflexAgent, GoalBasedAgent, UtilityBasedAgent)}


def agent_catalog():
    return [{"id": c.id, "name": c.name, "description": c.description} for c in AGENTS.values()]
