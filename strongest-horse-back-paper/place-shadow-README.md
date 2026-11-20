# £10 flat PLACE-only paper comparison (separate from the WIN strategy)

**Start date for new forward selections: Saturday 21 November 2026.**

This independent GitHub Actions workflow uses **the exact same horses and ranks from the already-locked** `strongest-horse-back-paper/YYYY-MM-DD-picks.json`. It does not choose any additional horses or generate ChatGPT conversations.

## Two £900 hypothetical accounts

- NAP-only: £10 fixed stake per eligible NAP.
- Top-three: £10 fixed stake per eligible published selection, including the NAP.
- NO progressive/martingale bets in this place trial. WIN portfolios remain unchanged.
- No selections are manufactured or substituted when the primary daily picks are missing.

## Official result and places

The program checks Sporting Life results, validates the race ID/date and horse, requires an official weighed-in result, determines the **actual starter count**, and obtains handicap status. Standard UK/Ireland bookmaker each-way place terms are applied:

| Actual runners | Race type | Places | Place fraction of WIN profit |
|---|---|---:|---:|
| 1–4 | Any | None | Skip place-only trial |
| 5–7 | Any | First 2 | 1/4 |
| 8–11 | Any | First 3 | 1/5 |
| 12–15 | Handicap | First 3 | 1/4 |
| 12–15 | Non-handicap | First 3 | 1/5 |
| 16+ | Handicap | First 4 | 1/4 |
| 16+ | Non-handicap | First 3 | 1/5 |

Source: https://support.betfair.com/app/answers/detail/a_id/10719/

These are *bookmaker each-way terms*, **NOT** Betfair Exchange PLACE market terms. Promotions/extra places are excluded. Non-runners are voided. Ambiguous results, dead heats on the placing boundary or unavailable sources remain pending rather than guessed.

## What the hypothetical P/L means

Our original **published pre-race bookmaker WIN reference** is the only price input. A synthetic place reference is calculated as:

`synthetic place decimal = 1 + ((locked WIN decimal - 1) × standard EW fraction)`

Example: WIN quote 3.00, 1/5 each-way term -> synthetic place decimal 1.40. A £10 place-only hypothetical on an eligible placed horse gives +£3.80 after a 5% illustrative commission on positive profit. If not placed, -£10. A void/no-bet/unpriced horse makes no monetary bank change.

**Critical limitation:** Bookmaker each-way place prices are normally offered as **part of an each-way bet**, not necessarily as a separate purchasable place-only bet; Betfair Exchange PLACE quotes are independent prices. Therefore these balances are research sensitivity scenarios, **not real or executable place-only profitability**, and must never be presented as evidence of available matched Exchange prices. A trading decision would require authentic historical/future Exchange PLACE market prices.

## Scheduled processing

The separate [GitHub Actions workflow](../../.github/workflows/horse-place-shadow.yml) runs at 11:27, 12:27, 20:27, 21:27, 22:27 and 23:27 UTC. It recalculates settled horses and keeps unresolved cases pending. It retries at later slots or the next day after a delayed or failed source response; no user attention required for routine missing results.

- Daily results: `strongest-horse-back-paper/place-shadow/YYYY-MM-DD-results.json`
- Cumulative two-account ledger: `strongest-horse-back-paper/place-shadow/status.json`
- Source: `independent_horse/place_shadow.py`
- Tests: `tests/test_place_shadow.py`

The earlier 16–20 November picks are *not* entered as fresh forward place bets, avoiding hindsight after changing the strategy. A live smoke check on 20 Nov correctly identified Current Edition's 3rd as an unplaced outcome for a race with **7 starters and 2 places**, without posting any retrospective wager.

**This remains strictly paper-only, £0 extra data budget, no real bets or betting APIs, no new ChatGPT task.** Candidate D, original WIN banks and historical picks are untouched.
