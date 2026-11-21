"""Place-only PAPER comparison from primary immutable win selections.

Starting 2026-11-21 only: old outcomes are not retrospectively counted as forward bets.
Illustrative standard each-way PLACE PORTION reference price, never a tradable
place-only Exchange quote. No new horse choices; no bet execution, no credentials.
"""
from __future__ import annotations
import argparse, json, logging, re, sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from independent_horse.runner import ROOT, UK, get, iso, listing, money, nonrunner, now_uk, off_time, slug

START=date(2026,11,21)
BASE=ROOT/"strongest-horse-back-paper"
OUT=BASE/"place-shadow"
LOG=logging.getLogger("place-shadow")
STAKE=Decimal("10")
COMMISSION=Decimal(".05")

def norm(text):
    s=slug(text).replace("-aw","").replace("-all-weather","")
    return s

def place_terms(starters,handicap):
    """Conventional UK/Ireland each-way PLACE PORTION terms; not Exchange market terms."""
    if starters<5:return None
    if starters<8:return {"places":2,"fraction":"0.25","basis":"5-7 starters"}
    if handicap and starters>=16:return {"places":4,"fraction":"0.25","basis":"handicap 16+ starters"}
    if handicap and starters>=12:return {"places":3,"fraction":"0.25","basis":"handicap 12-15 starters"}
    return {"places":3,"fraction":"0.20","basis":"standard 8+ starters"}

def locked_picks():
    for path in sorted(BASE.glob("????-??-??-picks.json")):
        if path.name[:10]<START.isoformat():continue
        try:
            d=json.loads(path.read_text("utf-8"))
            if d.get("date")!=path.name[:10]:continue
            if d.get("status") not in {"PRE_RACE_PICKS_LOCKED","PREDICTIONS_LOCKED_AWAITING_RESULTS"}:continue
            locked=datetime.fromisoformat(d["prediction_timestamp_uk"]).astimezone(UK)
            if locked.date().isoformat()!=d["date"]:continue
            yield d
        except (ValueError,KeyError,TypeError) as error:
            LOG.warning("Invalid primary pick document %s: %s",path,error)

def choose_card(pick,cards):
    """Match racecourse, scheduled off time AND (when published) race ID."""
    needle=norm(pick.get("racecourse",""))
    off=pick.get("race_time_uk","")
    hits=[c for c in cards
        if norm(c["course"])==needle and off_time(c["date"],c["off"])
        and off_time(c["date"],c["off"]).strftime("%H:%M")==off]
    # Only trust a unique race match, not a guessed 'nearest' event.
    if len(hits)!=1:
        raise ValueError(f"Cannot uniquely identify {needle} {off}: {len(hits)} candidates")
    return hits[0]

def result(pick,day,card):
    page,sha=get(card["result_url"],html=True)
    r=((page.get("props") or {}).get("pageProps") or {}).get("race") or {}
    head=r.get("race_summary") or {}
    rid=str((head.get("race_summary_reference") or {}).get("id") or "")
    if rid!=str(card["race_id"]) or str(head.get("date") or "")[:10]!=day:
        raise ValueError("Result belongs to another race/date")
    stage=str(head.get("race_stage") or "").upper()
    if stage in {"RACEVOID","VOID","ABANDONED"}:
        return {"status":"VOID","reason":stage,"source":card["result_url"]}
    if stage!="WEIGHEDIN":
        return {"status":"PENDING","reason":"Race result not yet officially weighed in","source":card["result_url"]}
    rides=[x for x in r.get("rides",[]) if isinstance(x,dict)]
    active=[x for x in rides if not nonrunner(x)]
    horse_matches=[x for x in rides if norm((x.get("horse") or {}).get("name",""))==norm(pick["horse"])]
    if len(horse_matches)!=1:
        raise ValueError("Cannot uniquely identify chosen horse in official results")
    horse=horse_matches[0]
    if nonrunner(horse):return {"status":"VOID","reason":"Non-runner","source":card["result_url"]}
    if not isinstance(head.get("has_handicap"),bool):
        raise ValueError("Race handicap status not verified")
    places=place_terms(len(active),head["has_handicap"])
    if places is None:
        return {"status":"INELIGIBLE","reason":"Fewer than five starters; no standard place-only reference",
            "starters":len(active),"source":card["result_url"]}
    def position(x):
        raw=x.get("amended_position")
        if raw is None or raw=="":raw=x.get("finish_position")
        try:return int(raw)
        except (ValueError,TypeError):return 0
    if not any(position(x)==1 for x in active):
        return {"status":"PENDING","reason":"No verified official winner","source":card["result_url"]}
    pos=position(horse)
    if pos==0:
        if not (horse.get("casualty") or {}).get("reason"):
            raise ValueError("Horse finishing position/nonfinish reason is unknown")
    # At a dead-heat on the place boundary, payoffs may be reduced.
    if pos==places["places"] and sum(0<position(x)<=pos for x in active)>places["places"]:
        raise ValueError("Dead heat at paid-place boundary; manual settlement required")
    win=pick.get("locked_win_reference_decimal")
    try:win=Decimal(str(win))
    except Exception:win=None
    if win is None or not win.is_finite() or win<=1:
        status="UNPRICED_FORECAST"
        return {"status":status,"placing":"PLACED" if pos and pos<=places["places"] else "UNPLACED",
            "position":pos or None,"starters":len(active),"places_paid":places["places"],
            "fraction":places["fraction"],"source":card["result_url"]}
    price=Decimal(1)+(win-1)*Decimal(places["fraction"])
    placed=bool(pos and pos<=places["places"])
    pnl=money(STAKE*(price-1)*(1-COMMISSION)) if placed else -STAKE
    return {"status":"PLACED" if placed else "UNPLACED","position":pos or None,
        "starters":len(active),"handicap":head["has_handicap"],"places_paid":places["places"],
        "fraction":places["fraction"],"terms_basis":places["basis"],
        "locked_win_reference_decimal":str(win),
        "illustrative_place_reference_decimal":str(price),
        "stake_gbp":str(STAKE),"pnl_gbp":str(pnl),
        "source":card["result_url"],"result_page_sha256":sha}

def stamped_picks(record):
    output=[]
    for s in record.get("selections",[]):
        ts=off_time(record["date"],s.get("race_time_uk"))
        if ts is None:continue
        # Never retrospectively admit a selection from after the scheduled off.
        locked=datetime.fromisoformat(record["prediction_timestamp_uk"]).astimezone(UK)
        if locked>=ts:continue
        output.append({"horse":s["horse"],"rank":s["rank"],
            "racecourse":s["racecourse"],"race_time_uk":s["race_time_uk"],
            "locked_win_reference_decimal":s.get("reference_price_decimal"),
            "original_lock_time_uk":iso(locked)})
    return output

def calculate(now):
    picks=list(locked_picks())
    updates={}
    for pickset in picks:
        day=pickset["date"]
        older=(now.date()-date.fromisoformat(day)).days
        if older<0:continue
        path=OUT/f"{day}-results.json"
        prev=json.loads(path.read_text("utf-8")) if path.exists() else None
        if prev and all(s.get("status") in {"PLACED","UNPLACED","INELIGIBLE","VOID"} or
                (s.get("status")=="UNPRICED_FORECAST" and s.get("locked_win_reference_decimal") is None)
                for s in prev.get("selections",[])):
            continue
        selection_rows=stamped_picks(pickset)
        if not selection_rows:continue
        use_feed=any(off_time(day,s["race_time_uk"])<now-timedelta(minutes=45) for s in selection_rows)
        cards=None;source_error=None
        if use_feed:
            try:cards,_,_=listing(day)
            except Exception as e:source_error=str(e)
        rows=[]
        for s in selection_rows:
            off=off_time(day,s["race_time_uk"])
            if off>now-timedelta(minutes=45):
                observation={"status":"PENDING","reason":"Race not yet due for final settlement"}
            elif source_error:
                observation={"status":"PENDING","reason":"Racecard feed unavailable: "+source_error[:250]}
            else:
                try:observation=result(s,day,choose_card(s,cards))
                except Exception as e:observation={"status":"PENDING","reason":str(e)[:250]}
            rows.append({**s,**observation})
        updates[path]={"date":day,"experiment":"Parallel £10 flat PLACE paper comparison",
            "locked_primary_picks":f"{day}-picks.json",
            "price_model":"Standard EW place-fraction of historical locked bookmaker WIN reference; synthetic PLACE-ONLY price, NOT exchange price, not an available stand-alone wager",
            "commission_on_positive_profit":"5% illustrative","selection_count":len(rows),
            "selections":rows}
    OUT.mkdir(parents=True,exist_ok=True)
    for path,data in updates.items():
        body=json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+"\n"
        if not path.exists() or path.read_text("utf-8")!=body:path.write_text(body,encoding="utf-8")
    summaries={}
    docs=sorted(OUT.glob("????-??-??-results.json"))
    for group in ("NAP-only","Top-three"):
        selected=[]
        for path in docs:
            d=json.loads(path.read_text("utf-8"))
            selected.extend([(d["date"],s) for s in d["selections"]
                if group=="Top-three" or s["rank"]==1])
        completed=[s for _,s in selected if s["status"] in {"PLACED","UNPLACED"}]
        wins=sum(s["status"]=="PLACED" for s in completed)
        pnl=sum((Decimal(s["pnl_gbp"]) for s in completed),Decimal(0))
        staked=STAKE*len(completed)
        summaries[group]={"bank_gbp":str(money(900+pnl)),"pnl_gbp":str(money(pnl)),
            "priced_settled":len(completed),"place_wins":wins,
            "place_losses":len(completed)-wins,
            "win_rate_pct":str(money(100*wins/len(completed))) if completed else None,
            "staked_gbp":str(staked),
            "roi_pct":str(money(100*pnl/staked)) if staked else None,
            "pending":sum(s["status"]=="PENDING" for _,s in selected),
            "unpriced":sum(s["status"]=="UNPRICED_FORECAST" for _,s in selected),
            "ineligible_or_void":sum(s["status"] in {"INELIGIBLE","VOID"} for _,s in selected)}
    status={"model":"synthetic-place-only-v1","forward_start_date":START.isoformat(),
        "as_of_uk":iso(now),"portfolios":summaries,
        "price_warning":"EW fraction-based PLACE-ONLY hypothetical prices are not actual Betfair Exchange place quotes; do not infer executability or profitability.",
        "no_new_selections":True,"no_real_bets":True}
    status_file=OUT/"status.json"
    body=json.dumps(status,indent=2,ensure_ascii=False)+"\n"
    if not status_file.exists() or status_file.read_text("utf-8")!=body:
        status_file.write_text(body,encoding="utf-8")
    LOG.info("Place comparison: %s",[(k,v["pnl_gbp"],v["priced_settled"],v["pending"]) for k,v in summaries.items()])

def smoke():
    # Real historic data, WITHOUT entering a retrospective bet in the forward ledger.
    d=json.loads((BASE/"2026-11-20-picks.json").read_text("utf-8"))
    cards,_,_=listing(d["date"])
    s=d["selections"][0]
    o=result(s,d["date"],choose_card(s,cards))
    if o["status"] not in {"PLACED","UNPLACED"}:raise ValueError("Historical race result not resolved")
    if o["position"]!=3:raise ValueError("Unexpected historical result")
    LOG.info("Place smoke: %s placed=%s, %s starters, %s places, synthetic odds %s",
             s["horse"],o["status"],o["starters"],o["places_paid"],
             o["illustrative_place_reference_decimal"])

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("mode",choices=["run","smoke"])
    args=ap.parse_args()
    logging.basicConfig(level=logging.INFO,format="%(levelname)s %(message)s")
    if args.mode=="smoke":smoke()
    else:calculate(now_uk())

if __name__=="__main__":
    try:main()
    except Exception:
        LOG.exception("Place comparison did NOT validate; no made-up record or returns")
        sys.exit(1)
