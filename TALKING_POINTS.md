# Talking points (for you, not the repo)

Read before an interview. These are decisions worth being able to explain
in your own words.

## "Why chess, for a Rocket League coaching company?"

Be direct about this — it's actually a good answer, not something to dance
around: "trophi.ai's core idea is turning gameplay data into personalized
coaching, starting with Rocket League. I wanted to show I understood that
idea generally, not just as a Rocket League feature, so I applied the same
pattern to a different competitive game where I could get real match data
easily." That's a stronger answer than pretending you're a serious Rocket
League player when you're not.

## "Walk me through what happens end to end"

1. `POST /api/profile?username=X` → `lichess_client.py` calls Lichess's
   public games API, requesting only games that have computer analysis
2. `parser.py` turns Lichess's raw JSON into `GameRecord` objects — this is
   the layer that knows Lichess's specific schema (player color, ply
   parity, judgment extraction)
3. `stats.py` aggregates: win/loss/draw rate, mistakes broken down by game
   phase, opening repertoire with per-opening win rates
4. `ai_coach.py` builds a prompt from those stats and calls Claude, which
   returns structured coaching feedback referencing the actual numbers
5. Frontend displays all of it, and is explicit about whether the data
   shown is live or fallback

## "Why does it fall back to synthetic data sometimes?"

Not every Lichess game gets computer analysis — casual/unrated games,
inactive accounts, or brand-new accounts often don't have enough analyzed
games. Rather than showing an error page for a large fraction of usernames
someone might type in, the app generates data in the exact same shape and
clearly labels it as such (`data_source: "fallback"`, and the frontend
shows a visible note). This is a real production pattern — graceful
degradation instead of a hard failure — not a workaround for something
that "doesn't really work."

## "How did you verify the parsing logic is actually correct?"

Point to `test_judgments_only_include_players_own_moves` specifically. Ply
numbering in Lichess's `analysis` array is 1-indexed, and a player's own
moves are either all-odd or all-even plies depending on their color. It
would be an easy, silent bug to attribute the *opponent's* blunders to the
player being analyzed. The fixture in `tests/fixtures/sample_games.ndjson`
is built from Lichess's real documented schema, and that specific test
exists because I found and fixed that exact mistake while building this —
worth saying openly if asked, since catching your own bug via a test is a
better story than never having made it.

## "What's the weakest part of this, honestly?"

Have a real answer ready, don't dodge:
- Game phase is a ply-count proxy, not based on material on the board —
  stated explicitly in the README rather than hidden
- No historical tracking — every analysis is a fresh snapshot, no "you're
  improving" trend over time
- No handling yet for very high-volume users beyond `max_games` — Lichess
  paginates and rate-limits, and a real production version would need to
  respect that more carefully for bulk exports

## "Why rely on Lichess's own judgment labels instead of computing
centipawn loss yourself?"

Because Lichess already computes it correctly, with thresholds the chess
community treats as standard. Recomputing blunder/mistake/inaccuracy
classification from raw eval numbers would mean re-deriving (and likely
getting subtly wrong) something already done well upstream. This is a
legitimate build-vs-reuse call, not corner-cutting — say that plainly if
asked.

## If asked something you don't remember

Say so, and trace through the actual code to answer live. That's a better
signal than a confident guess.
