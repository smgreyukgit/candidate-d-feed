# Strongest Horse Bets — Selection and Price Policy v2
Effective for new pre-race selections beginning 2026-11-18 00:00 Europe/London.
Policy change approved in conversation on 2026-11-17. Do not edit 2026-11-16 and 2026-11-17 locked pick records; no hindsight backdating.

## Purpose
The experiment tests whether independent, documented, FORM-BASED ChatGPT horse selections can identify winning UK/Irish horses and how PAPER progressive stakes would have performed. This is not an automated value-betting model or real betting system.

## Each racing morning (09:00 UK)
* Review fresh declared runners, off times, race types and reliable publicly available form.
* Prefer an evidence-based NAP (#1) when adequate facts are available; optionally #2/#3 shadows. No need to predict a numeric fair probability, prove an edge, or obtain live Betfair exchange quotes to rank form prospects.
* Independently weigh recent form, distance/surface/going suitability, strength of opposition, class, handicap/weights, trainer/jockey where available, and known risks. Do not copy other tipsters as the sole basis.
* Confirm horse identity, race, race time, and that the race has not started.
* Seek and freeze a published pre-off decimal quote with source and timestamp; credible bookmaker/racecard quote is permitted. A live Betfair exchange quote is optional.
* If reliable prices cannot be found but the form is supportable, record a timestamped FORECAST-ONLY pick for win-rate tracking, without inventing a price or calling it a paper bet for bankroll purposes. If no credible race/form support, NO BET is acceptable. Never force three.
* Include selection ranking, reason, risk, exact available price type, URL and selection timestamp. No unsubstantiated quantified probability or value claim. NEVER replace a locked pick after racing with a newly identified winner or a later price.

## Portfolio and paper simulation
* Distinct NAP-only portfolio and Top-3 portfolio (including NAP once).
* Within each: 3 independent virtual methods, each initially £900: flat £10; £10 × 1.5^prior losses capped £30; £10 × 2^prior losses capped £40. Win resets following stake to £10; loss increments, subject to caps; void/no-bet/unpriced forecast does not touch bank/progression.
* Settle portfolio bets by ACTUAL chronological race-off order, not predicted rank.
* PRIMARY paper P/L: 5% illustrative commission on profitable BACK bets calculated using the timestamped VERIFIED pre-race published reference decimal quote, with full stake deducted on a loss. These are hypothetical fixed-reference-price returns and NOT executable Betfair back prices. Never claim actual bets or profits.
* SECONDARY: log official Betfair BSP as an independent proxy when verified. NEVER quietly substitute the BSP into the primary series; preserve prices for possible historical staking replays and execution feasibility checks. For unpriced forecasts, record outcomes without changing the monetary ledgers.
* Existing 2026-11-16 wagers all lost; their deductions do not depend on odds. Existing 2026-11-17 NO BET remains unchanged.
* Show data-quality limitations, virtual-bank balances, ROI, streaks, and maximum drawdown, and selection count separately from priced stake-eligible count. Make no claim of profitability or future outcome from small samples.

## Journal
* Location: smgreyukgit/candidate-d-feed / strongest-horse-back-paper/
* Save immutable timestamped daily picks, dated results, standalone price provenance and rule version, status/bank state, and source links.
* If GitHub read/write unavailable, report error with self-contained rows; never silently pretend journal persisted.
* Preserve chronological records for later replay of any capped or uncapped staking system.
* PAPER ONLY — no real orders, no broker/bookmaker connections, no paid data or new subscriptions. Don't touch Candidate D or candidate_d_feed.txt.
