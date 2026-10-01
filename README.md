# Chess Coach

A web app that pulls a player's recent games from Lichess, finds where they're losing points, and gives coaching feedback based on their actual stats.

## Why I built this

I wanted a project that takes real, messy data and turns it into something a person can actually use, which ties into the data-focused courses I'm taking. Chess is a good fit because Lichess's public API returns computer analysis for analyzed games (move-by-move evaluations and mistake labels) for free. That meant I could work with real data instead of making it up, and focus on the analysis and the feedback.

## What it does

1. Fetches a player's recent analyzed games from the Lichess public API (no API key needed).
2. Breaks down inaccuracies, mistakes and blunders by game phase (opening, middlegame, endgame) and by opening.
3. Sends those stats to the Claude API, which writes a short summary, strengths, focus areas and practice suggestions.
4. Shows everything on a simple dashboard.

If a player doesn't have enough analyzed games, the app switches to sample data and labels it clearly on the page. If there's no Claude API key or the call fails, it uses template-based coaching instead.

## How it's built

- **Backend:** Python, FastAPI, Pydantic, httpx
- **Frontend:** HTML and JavaScript, served by the backend
- **AI:** Claude API (Anthropic SDK)
- **Testing:** pytest
- **Containers / cloud:** Dockerfile included, with a written guide for deploying to AWS ECS Fargate ([AWS_DEPLOY.md](AWS_DEPLOY.md))

The backend is split into small modules:

| File | What it does |
|---|---|
| `lichess_client.py` | Calls the Lichess games API |
| `parser.py` | Turns Lichess's JSON into a simple `GameRecord` format. It's the only file that knows about Lichess, so the rest of the code doesn't care where the data came from |
| `stats.py` | Calculates the phase and opening breakdowns |
| `ai_coach.py` | Builds the prompt, calls Claude, falls back to templates if needed |
| `fallback_data.py` | Generates sample games when live data isn't available |
| `main.py` | FastAPI routes |

## Things I ran into

**Counting the right player's mistakes.** Lichess's analysis covers every move in the game, from both players. Moves alternate between white and black, so the stats have to check whether each move belongs to the player being analyzed, based on the move's position and the player's colour. Getting this wrong would blame the player for their opponent's blunders, so there's a unit test specifically for this case.

**Not every game has analysis.** Computer analysis only exists for some games, so newer or casual accounts often don't have enough data. Instead of crashing or quietly showing fake numbers, the app falls back to sample data and the dashboard says so.

**Keeping the AI part optional.** The coaching depends on an external API that might be missing or down. The app checks for a key and catches failures, then uses template-based feedback so it always returns something useful.

**Known limitation:** game phase is based on move count (first 10 plies = opening, 11 to 30 = middlegame, after that = endgame) instead of the pieces left on the board. Counting material would be more accurate, and it's on my list.

## Running it locally

With Python:

```
cd backend
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # optional: add ANTHROPIC_API_KEY for AI coaching
uvicorn app.main:app --reload --port 8000
```

With Docker (from the project root):

```
docker build -t chess-coach -f backend/Dockerfile .
docker run -p 8000:8000 --env-file backend/.env chess-coach
```

Then open http://localhost:8000 and enter a Lichess username.

Run the tests:

```
cd backend
pytest tests/ -v
```

## What I'd add next

- Phase detection based on material instead of move count
- Time-trouble analysis using Lichess clock data
- Saving results over time to track improvement
- Linking to Lichess puzzles that match a player's weak spots
