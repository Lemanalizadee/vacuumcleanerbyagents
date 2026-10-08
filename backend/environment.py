"""
Task environment for the vacuum-cleaner agent  (PEAS from the course slides)

  Performance : +10 per unit of dirt cleaned, -1 for every action taken
  Environment : a rectangular room (grid) with obstacles and dirt of different amounts
  Actuators   : UP, DOWN, LEFT, RIGHT, SUCK, CHARGE   (NOOP = give up)
  Sensors     : dirt sensor, bump/obstacle sensors, battery sensor
                (+ a full map of the room for the agents that keep a model)
"""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Tuple

Pos = Tuple[int, int]

DIRS: Dict[str, Pos] = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}
REWARD_PER_UNIT = 10  # performance measure: reward for each unit of dirt removed


class World:
    def __init__(self, rows: int, cols: int, obstacles, dirt: Dict[Pos, int], start: Pos = (0, 0)):
        self.rows, self.cols = rows, cols
        self.start: Pos = (start[0], start[1])
        self.obstacles = {tuple(o) for o in obstacles}
        self.dirt: Dict[Pos, int] = dict(dirt)

    # ---------- geometry ----------
    def in_bounds(self, p: Pos) -> bool:
        return 0 <= p[0] < self.rows and 0 <= p[1] < self.cols

    def is_free(self, p: Pos) -> bool:
        return self.in_bounds(p) and p not in self.obstacles

    def move(self, p: Pos, action: str) -> Pos:
        dr, dc = DIRS[action]
        return (p[0] + dr, p[1] + dc)

    def free_neighbors(self, p: Pos):
        for action in DIRS:
            nxt = self.move(p, action)
            if self.is_free(nxt):
                yield action, nxt

    # ---------- (de)serialisation ----------
    def copy(self) -> "World":
        return World(self.rows, self.cols, set(self.obstacles), dict(self.dirt), self.start)

    def to_dict(self) -> dict:
        return {
            "rows": self.rows,
            "cols": self.cols,
            "start": list(self.start),
            "obstacles": sorted([list(o) for o in self.obstacles]),
            "dirt": [{"r": r, "c": c, "amount": a} for (r, c), a in sorted(self.dirt.items())],
        }

    @staticmethod
    def from_dict(d: dict) -> "World":
        rows, cols = d["rows"], d["cols"]
        start = (d["start"][0], d["start"][1])
        w = World(rows, cols, [], {}, start)
        for r, c in d.get("obstacles", []):
            if w.in_bounds((r, c)) and (r, c) != start:
                w.obstacles.add((r, c))
        for item in d.get("dirt", []):
            p = (item["r"], item["c"])
            if w.is_free(p) and p != start:
                w.dirt[p] = max(1, min(3, int(item.get("amount", 1))))
        return w

    # ---------- random room ----------
    @staticmethod
    def generate(size: int, dirt_density: float, obstacle_density: float, seed: int) -> "World":
        rng = random.Random(seed)
        start = (0, 0)
        for _ in range(30):  # retry until the robot is not walled in
            obstacles = {
                (r, c)
                for r in range(size)
                for c in range(size)
                if (r, c) != start and rng.random() < obstacle_density
            }
            w = World(size, size, obstacles, {}, start)
            dist, _ = bfs(w, start)  # dirt only where the robot can actually go
            if len(dist) >= 0.6 * (size * size - len(obstacles)) and len(dist) > 3:
                break
        candidates = [p for p in dist if p != start]
        rng.shuffle(candidates)
        n = max(1, round(dirt_density * len(candidates))) if candidates else 0
        for p in candidates[:n]:
            w.dirt[p] = rng.choice([1, 1, 2, 3])
        return w


def bfs(world: World, src: Pos):
    """Breadth-first search. Returns (distance map, parent map)."""
    dist = {src: 0}
    parent: Dict[Pos, Tuple[Pos, str]] = {}
    q = deque([src])
    while q:
        cur = q.popleft()
        for action, nxt in world.free_neighbors(cur):
            if nxt not in dist:
                dist[nxt] = dist[cur] + 1
                parent[nxt] = (cur, action)
                q.append(nxt)
    return dist, parent


def path_actions(parent, src: Pos, dst: Pos) -> List[str]:
    actions: List[str] = []
    cur = dst
    while cur != src:
        prev, action = parent[cur]
        actions.append(action)
        cur = prev
    return actions[::-1]


@dataclass
class Percept:
    """What the environment gives the agent on every step."""
    pos: Pos
    dirty: int                 # dirt sensor: amount of dirt on the current square (0 = clean)
    blocked: Dict[str, bool]   # bump sensors: is there a wall/obstacle in each direction?
    battery: int
    battery_max: int
    world: World               # full map: ONLY model-based agents (goal / utility) may use it
