# Independent Horse Paper — Parallel Runner (v1)

**Status:** Installed, GitHub Actions source smoke test passed on 19 Nov 2026 (7 unit tests, 34 UK/Irish racecards retrieved). **Not yet validated by a complete scheduled morning selection + evening settlement cycle.**

This is an independent, rule-based **SHADOW** experiment. It is intentionally separate from the existing form-judgement ChatGPT selections and Candidate D; results MUST NOT be merged or compared as if the methods were identical. No real betting, no execution APIs, no purchased data, no bookmaker accounts.

## Files

- Workflow: [`.github/workflows/independent-shadow-horse.yml`](../../.github/workflows/independent-shadow-horse.yml)
- Program: [`independent_horse/runner.py`](../../independent_horse/runner.py)
- Tests: [`tests/test_independent_horse.py`](../../tests/test_independent_horse.py)
- Daily locked selections: `strongest-horse-back-paper/independent-shadow/YYYY-MM-DD-picks.json`
- Append-only race result observations: `strongest-horse-back-paper/independent-shadow/results/YYYY-MM-DD/YYYY-MM-DDTHHMMSSZ.json`
- Current derived status: `strongest-horse-back-paper/independent-shadow/status.json`

## What actually runs

GitHub Actions invokes independent Python code at multiple possible slots:
- Morning: 08:17, 09:17, 10:17 and 11:17 **UTC**; code requires 09:00–12:59 **Europe/London**, locks only the first valid pre-race record and excludes races less than 65 minutes away. Redundant runs are retries, never additional selections.
- Evening: 20:17, 21:17, 22:17 **UTC**; reconciles up to 7 prior days of unresolved shadow selections. Verifies race identity/date, explicitly weighed-in stage and finishing place; unresolved results remain pending.
- Every source-code change triggers a **smoke test only**; never retrospective predictions.

GitHub's scheduled executions can be delayed/skipped, so no independent cloud schedule is infallible. A source failure exits nonzero, triggers a GitHub Actions failure, and attempts to open a GitHub issue. It is NOT silently translated into NO BET.

## Independent method and limitations

Source: public **Sporting Life** UK/Irish racecards and result pages, including `__NEXT_DATA__` data. The internal listing URL is undocumented and may change. This was explicitly checked on 19 Nov 2026, but reliability across multiple days remains unproven.

For each race, require at least four declared runners and at least two form finishes, one top-three in recent form, 4–180 days since a run. Rank the eligible horses using a fixed, auditable score from recent placing digits, recent wins, rest and within-field official ratings; prefer clear leader over close ties and take at most one per race. Lock up to three separate race leaders ranked by score. **Not** a trained probability model, ChatGPT judgement, deep full-form analysis or evidence of an edge. It does not yet evaluate course/trip/ground/pace suitability in sufficient depth. All uncertainty is disclosed.

Use Sporting Life's captured **bookmaker reference odds** for hypothetical staking when published; otherwise report an **unpriced forecast only**. Do not silently substitute later bookmaker prices, starting prices or Betfair BSP. Never claim a matched Exchange fill.

## Separate £900 paper portfolios

NAP-only and Top-three, each with £10 flat, ×1.5 capped at £30, and ×2 capped at £40. Loss increases the *next* qualifying stake, win resets it to £10. No-bet, void and unpriced forecasts leave monetary ledgers unchanged. Apply 5% illustrative commission on positive back-profit. Staking replay always uses **chronological race times**, blocks later calculations after earlier pending results and refuses unaffordable stakes. Replays are recalculated from immutable picks and append-only result observations, so alternative stakes can later be compared without changing predictions.

## Testing and promotion policy

First verify several complete scheduled cycles and real reference-quote coverage. Do **not** stop the original ChatGPT selection or results tasks or promote shadow outcomes to primary without comparing selection quality, missing data and journal integrity. The existing ChatGPT ledger and Candidate D stay untouched.

GitHub Actions status: https://github.com/smgreyukgit/candidate-d-feed/actions/workflows/independent-shadow-horse.yml

All infrastructure is existing/free; no paid racing API required. This doesn't guarantee uninterrupted free access to the Sporting Life site.