# Vacuum Cleaner – Intelligent Agents (FastAPI + HTML/JS)

A grid-room simulation of the vacuum-cleaner example from the "Intelligent Agents" slides.
Three agent programs run in the same task environment so you can compare them.

## Run it
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```
Open http://127.0.0.1:8000 and press **Run**.

## Structure
```
backend/
  environment.py  PEAS task environment: World, sensors (Percept), BFS helpers
  agents.py       SimpleReflexAgent, GoalBasedAgent, UtilityBasedAgent
  simulation.py   environment <-> agent loop, returns every step as a "frame"
  main.py         FastAPI endpoints + serves the frontend
frontend/
  index.html, style.css, app.js   canvas animation, controls, comparison table
```

## PEAS
| | |
|---|---|
| Performance | +10 per unit of dirt cleaned, −1 per action |
| Environment | grid room, obstacles, dirt of amount 1–3, charger at the start square |
| Actuators | UP, DOWN, LEFT, RIGHT, SUCK, CHARGE |
| Sensors | dirt sensor, bump sensors (4 directions), battery level, full map (model-based agents only) |

## Agents
- **Simple reflex** – `if dirty: SUCK else: random free direction`. Uses only the current percept.
- **Goal-based** – knows the map, goal = "no dirt left", plans the shortest path (BFS) to the nearest dirt. Ignores battery.
- **Utility-based** – utility `U = 10·amount / (distance+1)`; only picks targets it can still return from; goes to CHARGE when needed.

With the default battery (40) the reflex and goal-based agents run out of power while the
utility-based agent recharges and finishes – that is the point of the comparison. Raise the battery slider to see them all succeed.

## API
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/agents` | list agents |
| GET | `/api/world?size=10&dirt=0.15&obstacles=0.15&seed=1` | generate a room |
| POST | `/api/simulate` | `{world, agent, battery, max_steps, seed}` → `{frames, summary}` |
| POST | `/api/compare` | run all agents on the same room → summaries |
Interactive docs: http://127.0.0.1:8000/docs

## Add your own agent
Create a class in `backend/agents.py` with `id`, `name`, `description` and `act(percept) -> (action, reason)`,
then add it to the `AGENTS` tuple. It appears in the UI automatically.
