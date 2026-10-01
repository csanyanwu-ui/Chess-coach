# Chess Coach

Pulls a player's recent games from Lichess, analyzes where they're actually
losing points — by game phase, by opening — and generates specific,
data-grounded coaching feedback with Claude.

**Live demo:** _[]_

## Why chess

trophi.ai's pitch is turning gameplay data into personalized coaching —
starting with sim racing and Rocket League. Chess is a clean second proof
of the same idea: competitive game, publicly available match data, and a
real gap between "here's what happened" and "here's what to actually work
on." Lichess also makes this unusually easy to do *properly*: its public
API returns real computer analysis (move-by-move evaluations and
inaccuracy/mistake/blunder judgments) for free, with no API key required —
so this project pulls live data by default instead of mocking it.

## What it does

1. Fetches a Lichess user's recent **analyzed** games via the public API.
2. Breaks down mistakes by **game phase** (opening / middlegame / endgame)
   and by **opening repertoire**, so patterns are visible instead of buried
   in a single aggregate blunder count.
3. Sends those stats to Claude, which generates a summary, strengths, focus
   areas, and specific practice suggestions grounded in the real numbers.
4. Displays it all in a dashboard.

If a username has too few analyzed games (common for new or casual
accounts — not every game gets computer analysis), the app **falls back to
clearly-labeled synthetic data** rather than failing outright or silently
pretending it's real. The frontend shows which one you're looking at.

## Architecture

```
┌──────────┐   ┌───────────────────────────────────────────────────┐
│ Frontend │──▶│ FastAPI backend                                    │
│ (HTML/JS)│   │ ┌───────────────┐ ┌────────┐ ┌───────┐ ┌─────────┐│
│          │◀──│ │lichess_client │▶│ parser │▶│ stats │▶│ai_coach ││
└──────────┘   │ └───────┬───────┘ └────────┘ └───────┘ └────┬────┘│
                │         │ (fails / too few games)           │     │
                │         ▼                                    ▼     │
                │  ┌──────────────┐                     Claude API  │
                │  │fallback_data │              (falls back to     │
                │  └──────────────┘               template if no    │
                └───────────────────────────────── key or call fails)┘
```

- **`lichess_client.py`** — real HTTP calls to Lichess's public games API (no auth needed).
- **`fallback_data.py`** — synthetic data generator matching the same `GameRecord` shape, used only when live data is unavailable, and clearly flagged as such via `data_source` in the API response.
- **`parser.py`** — Lichess-specific JSON parsing. This is the only file that knows Lichess's schema; everything past it works off `GameRecord`.
- **`stats.py`** — pure functions: phase-based mistake breakdown, opening repertoire win rates. Unit tested against a realistic fixture, including a test that specifically catches a ply-parity bug (attributing the opponent's blunders to the player).
- **`ai_coach.py`** — builds the coaching prompt, calls Claude, falls back to deterministic template coaching if no API key is set or the call fails.
- **`main.py`** — FastAPI routes; serves the frontend as static files from the same container.

### A deliberate simplification, stated plainly

Game phase is approximated by **ply count** (opening = first 10 plies,
middlegame = 11-30, endgame = beyond) rather than counting pieces on the
board. A material-based phase detector would be more accurate but wasn't
worth the time on this build — this is called out in the code comments,
not hidden.

## Running locally

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # optional — add ANTHROPIC_API_KEY for real AI coaching
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000`, enter any active Lichess username (e.g. a
username you recognize from lichess.org), click **Analyze recent games**.

Run tests:
```bash
pytest tests/ -v
```

## Deploying to AWS

See [`AWS_DEPLOY.md`](./AWS_DEPLOY.md) for the full ECS Fargate walkthrough.

## What's next

- **Real material-based phase detection** instead of the ply-count proxy.
- **Time-trouble analysis** — Lichess includes per-move clock data in PGN
  comments; parsing that would add "you're blundering when low on time"
  as its own coaching signal.
- **Historical trend tracking** — store profiles over time (Postgres) to
  show "your blunder rate is improving" instead of a single snapshot.
- **Puzzle recommendations** — Lichess also has a public puzzle API; drills
  could link directly to puzzles matching a player's specific weakness
  instead of just describing what to practice.
- **Infrastructure as code** — the AWS steps are manual for now; Terraform
  or CDK would make deployment reproducible.

## Tech stack

FastAPI · Pydantic · httpx · Lichess public API · Claude API (Anthropic SDK) · vanilla JS/HTML frontend · Docker · AWS ECS Fargate
