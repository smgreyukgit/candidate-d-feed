# One-off PLACE-market retrospective — provisional research result

**Dates:** 16, 18, 19 and 20 November 2026  
**Sample:** All 11 already-locked original horse selections, including NAPs and shadows  
**Method:** Hypothetical £10 back-to-place stake per eligible original pick, 5% illustrative commission only on positive bet profit, no progression, no new predictions

## Baseline result — conditional on standard actual-starter market assumption

| Portfolio | Picks | Priced | Placed | Unplaced | Excluded | Scenario P/L | Bank from £900 |
|---|---:|---:|---:|---:|---:|---:|---:|
| NAP-only | 4 | 3 | 2 | 1 | 1 | **−£0.59** | £899.41 |
| Top-three | 11 | 10 | 6 | 4 | 1 | **−£19.94** | £880.06 |

This is **not independently Betfair-verified BSP P/L**. Official Betfair free PLACE CSVs were reachable by URL but returned **HTTP 403** from GitHub Actions for all four dates. Instead, this report uses a third-party archive's published **Top 2 / Top 3 / Top 4 BSP**. We matched all 11 original picks by course, date, time and horse name; ten were included in the baseline and one was excluded on the starter-count assumption.

The underlying machine-readable records:
- [11 matched picks, market and P/L JSON](2026-11-16_to_2026-11-20-third-party-place-bsp.json)
- [11 matched picks CSV](2026-11-16_to_2026-11-20-third-party-place-bsp.csv)

**Sources:**
- Third-party figures: https://stablewhispers.co.uk/fast-results/
- Betfair official free history: https://promo.betfair.com/betfairsp/SP_history.html
- **Crucial Exchange rule:** https://www.betfair.com/aboutUs/Rules.and.Regulations/ — for 'to be placed' markets, the number of winners is set out in market information and determined by runners known **when the market was loaded**, rather than automatically recalculated from actual starters.

## Material uncertainty: this could change the result

1. **Current Edition, Ascot 20 Nov:** The locked pick recorded **eight declared runners**, but only **seven ran** after a non-runner. Horse finished **third**. The baseline assumed *Top 2* (loss of £10), but if the Exchange market was originally set at *Top 3*, the third-party archive reports BSP **1.26**, making a £10 hypothetical **+£2.47**. This would improve each portfolio by **£12.47**.
2. **Old Park Star, Ffos Las 18 Nov:** **Four actually ran**. Baseline excludes the horse, assuming no live Place market at the time of racing. However, if a Place market was previously loaded with more declarations and remained active, the existing **Top 2** market might have been lost (the horse was third): a possible additional **−£10** in each portfolio. **Do not assume such a market existed or that it would have remained active.**
3. **Other race-specific market terms, withdrawals, dead heats and price provenance:** We haven't independently validated the exact Betfair **market IDs**, their **numberOfWinners**, original start-time rules, reduction factors or whether all third-party BSP columns are authentic market SPs.

Sensitivity illustrations using only the two documented ambiguous races:

| Scenario | NAP-only | Top-three |
|---|---:|---:|
| Baseline, inferred from actual starters | −£0.59 | −£19.94 |
| Current Edition market originally Top 3 | +£11.88 | −£7.47 |
| Old Park Star counted as a losing Top 2 market | −£10.59 | −£29.94 |
| Both alternative assumptions | +£1.88 | −£17.47 |

**These are scenarios, not a credible forecast or guaranteed full range.** Other exchange-market and third-party-price uncertainties are unresolved. No historical picks or current forward WIN/PLACE paper-bank balances were modified.

## Takeaway

The original horse selection method appears to have selected several horses finishing near the front, but at **very short place-market prices**. There is **no demonstrated profitable Place-market strategy** in this tiny sample. In particular, `Top-three` is negative even in the Current Edition Top-3 variant. Collect authenticated Exchange Place market IDs, BSP and settled results before drawing stronger conclusions.

**No real bets, no extra subscriptions, no new ChatGPT automation.**
