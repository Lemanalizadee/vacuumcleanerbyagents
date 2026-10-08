"""FastAPI backend.  Run from the project root:   uvicorn backend.main:app --reload"""
from __future__ import annotations

import random
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agents import AGENTS, agent_catalog
from .environment import World
from .simulation import simulate

app = FastAPI(title="Vacuum Cleaner - Intelligent Agents")


class DirtModel(BaseModel):
    r: int
    c: int
    amount: int = Field(1, ge=1, le=3)


class WorldModel(BaseModel):
    rows: int = Field(ge=3, le=30)
    cols: int = Field(ge=3, le=30)
    start: List[int] = [0, 0]
    obstacles: List[List[int]] = []
    dirt: List[DirtModel] = []


class SimulateRequest(BaseModel):
    world: WorldModel
    agent: str
    battery: int = Field(40, ge=1, le=5000)
    max_steps: int = Field(400, ge=1, le=5000)
    seed: Optional[int] = None


class CompareRequest(BaseModel):
    world: WorldModel
    battery: int = Field(40, ge=1, le=5000)
    max_steps: int = Field(400, ge=1, le=5000)
    seed: Optional[int] = None


@app.get("/api/agents")
def agents():
    return agent_catalog()


@app.get("/api/world")
def new_world(
    size: int = Query(10, ge=4, le=24),
    dirt: float = Query(0.15, ge=0.01, le=0.8),
    obstacles: float = Query(0.15, ge=0.0, le=0.45),
    seed: Optional[int] = None,
):
    seed = random.randrange(1_000_000) if seed is None else seed
    world = World.generate(size, dirt, obstacles, seed).to_dict()
    world["seed"] = seed
    return world


@app.post("/api/simulate")
def run(req: SimulateRequest):
    if req.agent not in AGENTS:
        raise HTTPException(404, f"Unknown agent '{req.agent}'")
    return simulate(req.world.model_dump(), req.agent, req.battery, req.max_steps, req.seed)


@app.post("/api/compare")
def compare(req: CompareRequest):
    """Run every agent on the SAME room and return only the summaries."""
    return [
        {**simulate(req.world.model_dump(), aid, req.battery, req.max_steps, req.seed)["summary"],
         "name": cls.name}
        for aid, cls in AGENTS.items()
    ]


# Serve the frontend (must be mounted last)
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
