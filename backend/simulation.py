"""Runs one episode: environment <-> agent loop. Returns every step so the frontend can animate it."""
from __future__ import annotations

from typing import Optional

from .agents import AGENTS
from .environment import DIRS, REWARD_PER_UNIT, Percept, World


def simulate(world_dict: dict, agent_id: str, battery: int = 40, max_steps: int = 400,
             seed: Optional[int] = None) -> dict:
    world = World.from_dict(world_dict)
    total_dirt_cells = len(world.dirt)
    agent = AGENTS[agent_id](seed)

    pos = world.start
    score = cleaned = recharges = bumps = 0
    status = None
    frames = [{
        "step": 0, "pos": list(pos), "action": "START", "reason": "Initial state",
        "battery": battery, "score": 0, "cleaned": 0, "removed": None, "bump": False,
    }]

    for step in range(1, max_steps + 1):
        if not world.dirt:
            break
        percept = Percept(
            pos=pos,
            dirty=world.dirt.get(pos, 0),
            blocked={a: not world.is_free(world.move(pos, a)) for a in DIRS},
            battery=battery,
            battery_max=battery if step == 1 else frames[0]["battery"],
            world=world,
        )
        action, reason = agent.act(percept)

        if action == "NOOP":
            status = "stuck"
            break
        if battery <= 0 and action != "CHARGE":
            status = "battery_dead"
            break

        removed, bump = None, False
        if action in DIRS:
            nxt = world.move(pos, action)
            if world.is_free(nxt):
                pos = nxt
            else:
                bump = True
                bumps += 1
            battery -= 1
            score -= 1
        elif action == "SUCK":
            amount = world.dirt.pop(pos, 0)
            if amount:
                score += REWARD_PER_UNIT * amount
                cleaned += 1
                removed = list(pos)
            battery -= 1
            score -= 1
        elif action == "CHARGE":
            if pos == world.start:
                battery = frames[0]["battery"]
                recharges += 1
            score -= 1

        frames.append({
            "step": step, "pos": list(pos), "action": action, "reason": reason,
            "battery": battery, "score": score, "cleaned": cleaned,
            "removed": removed, "bump": bump,
        })

    if not world.dirt:
        status = "clean"
    elif status is None:
        status = "max_steps"

    return {
        "frames": frames,
        "summary": {
            "agent": agent_id, "status": status, "steps": len(frames) - 1,
            "score": score, "cleaned": cleaned, "total_dirt": total_dirt_cells,
            "battery_left": battery, "recharges": recharges, "bumps": bumps,
        },
    }
