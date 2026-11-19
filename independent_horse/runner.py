"""Independent rule-based horse selections and results: SHADOW/PAPER ONLY.
No bookmaker/Betfair credentials, no order placement, no ChatGPT scheduler.
Data source: Sporting Life's public racecards and result pages. This source may change.
"""
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, logging, math, os, re, sys, time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"strongest-horse-back-paper"/"independent-shadow"
UK=ZoneInfo("Europe/London")
SITE="https://www.sportinglife.com"
LOG=logging.getLogger("independent-horse")
NEXT=re.compile(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',re.S)
UKIRE={"england","scotland","wales","ireland","northern ireland","great britain","united kingdom","eire"}
COURSES=set(("aintree ascot ayr bangor-on-dee bath beverley brighton carlisle cartmel catterick "
"chelmsford-city cheltenham chepstow chester doncaster epsom exeter fakenham ffos-las fontwell "
"goodwood hamilton haydock hereford hexham huntingdon kelso kempton leicester lingfield ludlow "
"market-rasen musselburgh newbury newcastle newmarket newton-abbot nottingham perth plumpton "
"pontefract redcar ripon salisbury sandown sedgefield southwell stratford taunton thirsk "
"uttoxeter warwick wetherby wincanton windsor wolverhampton worcester yarmouth york "
"cork curragh down-royal downpatrick dundalk fairyhouse galway gowran-park kilbeggan "
"killarney laytown leopardstown limerick listowel naas navan punchestown roscommon "
"sligo thurles tipperary tramore wexford").split())

class SourceFailure(Exception):pass
def now_uk():return datetime.now(UK)
def iso(t):return t.astimezone(UK).isoformat(timespec="seconds")
def slug(s):return re.sub("[^a-z0-9]+","-",str(s).lower()).strip("-")
def money(x):return Decimal(str(x)).quantize(Decimal(".01"),rounding=ROUND_HALF_UP)
def read(path):return json.loads(path.read_text(encoding="utf-8"))
def write_once(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644),"w",encoding="utf-8") as f:
        json.dump(obj,f,indent=2,ensure_ascii=False,allow_nan=False);f.write("\n")

def get(url, html=False):
    error=None
    for n in range(3):
        try:
            request=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; paper-racing-research/1.0)",
                "Accept":"application/json,text/html","Accept-Language":"en-GB,en;q=0.9"})
            with urlopen(request,timeout=25) as response:content=response.read(5_000_000)
            digest=hashlib.sha256(content).hexdigest()
            if html:
                match=NEXT.search(content.decode("utf-8"))
                if not match:raise SourceFailure("No embedded race data (website format changed): "+url)
                return json.loads(match.group(1)),digest
            return json.loads(content),digest
        except (HTTPError,URLError,TimeoutError,OSError,ValueError) as exc:
            error=exc
            if isinstance(exc,HTTPError) and exc.code<500 and exc.code not in (408,425,429):break
            if n<2:time.sleep(2*(n+1))
    raise SourceFailure(f"Source request failed at {url}: {error}")

def listing(day):
    url=f"{SITE}/api/horse-racing/racing/racecards/{day}"
    raw,digest=get(url)
    if not isinstance(raw,list):raise SourceFailure("Malformed UK/Irish racecard listing")
    cards=[]
    for meeting in raw:
        if not isinstance(meeting,dict):continue
        meta=meeting.get("meeting_summary") or {}
        course=meta.get("course") or {}
        country=course.get("country") or {}
        c=country.get("long_name","").lower() if isinstance(country,dict) else ""
        name=course.get("name","")
        if not ((c in UKIRE) if c else (slug(name) in COURSES)):continue
        for race in meeting.get("races") or []:
            rid=str((race.get("race_summary_reference") or {}).get("id") or "")
            race_day=str(race.get("date") or meta.get("date") or day)[:10]
            if not rid or race_day!=day:continue
            rname=race.get("name") or "race"
            cards.append({"race_id":rid,"course":name,"name":rname,"off":race.get("time"),
                "url":f"{SITE}/racing/racecards/{day}/{slug(course.get('name',''))}/racecard/{rid}/{slug(rname)}",
                "result_url":f"{SITE}/racing/results/{day}/{slug(course.get('name',''))}/{rid}/{slug(rname)}",
                "date":day})
    if not cards:raise SourceFailure("No qualifying UK/Irish card links; feed missing or changed")
    return cards,url,digest

def off_time(day,value):
    m=re.search(r"\b(\d{1,2})[:.](\d{2})\b",str(value or ""))
    if not m:return None
    hh,mm=map(int,m.groups())
    return datetime.fromisoformat(day).replace(hour=hh,minute=mm,tzinfo=UK) if hh<24 and mm<60 else None

def nonrunner(r):
    return re.sub(r"[^A-Z]","",str(r.get("ride_status","")).upper()) in {"NONRUNNER","WITHDRAWN"}

def form_digits(value):
    # P/F/U/R/0 count as bad form; no post-race information used.
    chars=re.findall(r"[0-9PFURB]",str(value or "").upper())
    return [int(c) if c.isdigit() and c!="0" else 10 for c in chars[-5:]]

def odds(value):
    s=re.sub("[fj]+$","",str(value or "").lower().replace(" ",""))
    if s in {"evs","evens","ev"}:return 2.0
    m=re.fullmatch(r"(\d+)/(\d+)",s)
    if m and int(m.group(2)):return round(1+int(m.group(1))/int(m.group(2)),4)
    try:
        v=float(s)
        return round(v,4) if math.isfinite(v) and 1.01<=v<=1000 else None
    except ValueError:return None

def price_of(r):
    # bookmakerOdds is the only quote admitted to the monetary ledger.
    # Betting.current_odds has insufficient bookmaker provenance.
    books=r.get("bookmakerOdds") or []
    if not isinstance(books,list):books=[]
    for b in sorted((x for x in books if isinstance(x,dict)),key=lambda x:not x.get("bestOdds",False)):
        q=odds(b.get("fractionalOdds") or b.get("decimalOdds"))
        if q:
            label=b.get("bookmaker") or b.get("bookmakerName") or b.get("name")
            if isinstance(label,dict):label=label.get("name")
            return q,str(label) if label else None
    return None,None

def rating(r,top):
    h=r.get("horse") or {}
    history=form_digits((h.get("formsummary") or {}).get("display_text",""))
    try:days=int(h.get("last_ran_days"))
    except (ValueError,TypeError):days=None
    try:official=int(r.get("official_rating") or 0)
    except (ValueError,TypeError):official=0
    if nonrunner(r) or len(history)<2 or days is None or not 4<=days<=180 or not any(n<=3 for n in history):return None
    last=history[-3:]
    weights={1:8,2:6,3:4,4:2,5:1}
    value=sum(weights.get(p,0)*(i+1) for i,p in enumerate(last))
    value+=3*sum(p==1 for p in history)
    if 10<=days<=60:value+=3
    if official and top:value+=max(-4,4-(top-official)*.25)
    return {"score":round(value,2),"form_numbers":history,"days_since_last_run":days,
            "official_rating":official,"last_three_top_three":sum(p<=3 for p in last)}

def race_leader(card,now):
    off=off_time(card["date"],card["off"])
    if not off or off<now+timedelta(minutes=65):return None
    raw,digest=get(card["url"],html=True)
    race=((raw.get("props") or {}).get("pageProps") or {}).get("race") or {}
    head=race.get("race_summary") or {}
    sid=str((head.get("race_summary_reference") or {}).get("id") or "")
    if sid!=card["race_id"] or str(head.get("date") or card["date"])[:10]!=card["date"]:
        raise SourceFailure("Race identity/date mismatch: "+card["url"])
    rides=race.get("rides")
    if not isinstance(rides,list) or not rides:raise SourceFailure("No runner data in card "+card["url"])
    entries=[r for r in rides if isinstance(r,dict) and not nonrunner(r)]
    if not 4<=len(entries)<=16:return None
    tops=[]
    for r in entries:
        try:tops.append(int(r.get("official_rating") or 0))
        except (ValueError,TypeError):pass
    top=max(tops,default=0)
    candidates=[]
    for r in entries:
        h=r.get("horse") or {}
        name=h.get("name")
        hid=str((h.get("horse_reference") or {}).get("id") or "")
        stat=rating(r,top)
        if not name or not hid or not stat:continue
        quote,bk=price_of(r)
        candidates.append({"horse":name,"horse_id":hid,"race_id":sid,"racecourse":card["course"],
          "race":head.get("name") or card["name"],"race_time_uk":off.strftime("%H:%M"),
          "off_datetime_uk":iso(off),"race_class":head.get("race_class"),"distance":head.get("distance"),
          "going":head.get("going"),"form":(h.get("formsummary") or {}).get("display_text"),
          "jockey":(r.get("jockey") or {}).get("name") if isinstance(r.get("jockey"),dict) else None,
          "trainer":(r.get("trainer") or {}).get("name") if isinstance(r.get("trainer"),dict) else None,
          "field_size":len(entries),"metric_evidence":stat,
          "reference_price_decimal":quote,"reference_price_type":"Sporting Life published bookmaker reference" if quote else "UNPRICED_FORECAST",
          "reference_bookmaker":bk,"price_eligible":quote is not None,
          "price_observation_timestamp_uk":iso(now_uk()),"source_url":card["url"],
          "card_sha256":digest,"result_url":card["result_url"]})
    candidates.sort(key=lambda r:(-r["metric_evidence"]["score"],r["horse"]))
    if not candidates:return None
    best=candidates[0]
    if best["metric_evidence"]["score"]<18:return None
    if len(candidates)>1 and best["metric_evidence"]["score"]-candidates[1]["metric_evidence"]["score"]<2:return None
    ev=best["metric_evidence"]
    best["rationale"]=f"Recorded form {best['form']}, {ev['last_three_top_three']} top-three finishes in latest three, {ev['days_since_last_run']} days off; official rating {ev['official_rating'] or 'unavailable'}."
    best["risk"]="Rule considers form and ratings but not full historical suitability to class, pace, track or going. No proven betting edge."
    best["score_margin_to_next_eligible"]=round(ev["score"]-candidates[1]["metric_evidence"]["score"],2) if len(candidates)>1 else None
    return best

def morning(now):
    day=now.date().isoformat()
    out=BASE/f"{day}-picks.json"
    if out.exists():
        LOG.info("Previously LOCKED predictions found; no hindsight reselection")
        return
    if now.hour<9 or now.hour>12:
        LOG.info("Outside UK 09:00-12:59 pre-race processing window")
        return
    cards,url,digest=listing(day)
    # Written out explicitly to avoid guessing or silently including races already off.
    eligible=[c for c in cards if off_time(day,c["off"]) and off_time(day,c["off"])>=now+timedelta(minutes=65)]
    if not eligible:raise SourceFailure("No races safely in future; no hindsight bets")
    candidates=[];failed=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures={pool.submit(race_leader,c,now):c for c in eligible}
        for f in concurrent.futures.as_completed(futures):
            try:
                candidate=f.result()
                if candidate:candidates.append(candidate)
            except Exception as e:failed.append({"race_id":futures[f]["race_id"],"error":str(e)[:200]})
    if len(failed)>=max(3,math.ceil(len(eligible)*.75)):
        raise SourceFailure(f"Racecards failed for {len(failed)}/{len(eligible)}; not a legitimate NO BET day")
    candidates.sort(key=lambda x:(-x["metric_evidence"]["score"],x["horse"]))
    picks=candidates[:3]
    for i,p in enumerate(picks,1):
        p["rank"]=i
        p["label"]="NAP" if i==1 else "Shadow"
    record={"source_system":"independent-shadow-v1","date":day,"locked_at_uk":iso(now),
      "status":"PRE_RACE_PICKS_LOCKED" if picks else "NO_BET_FORM_CRITERIA",
      "source_list_url":url,"listing_sha256":digest,"races_checked":len(eligible),
      "source_errors":failed,"selection_method":"Fixed published form/recency/official-rating scoring heuristic, not ChatGPT or an expected-value model",
      "price_convention":"Published bookmaker reference observed before off, hypothetical 5% fee on win profit. NOT Betfair exchange matched odds or BSP.",
      "no_bet_reason":"No race leader met predeclared form and score thresholds" if not picks else None,
      "selections":picks,"no_real_bets":True,"separate_from_chatgpt_primary":True}
    write_once(out,record)
    LOG.info("LOCKED shadow picks: %s",[(x["horse"],x["race_time_uk"],x["reference_price_decimal"]) for x in picks])

def result_for(s,day):
    url=s.get("result_url")
    if not url:return {"outcome":"PENDING","reason":"No result URL locked"}
    raw,digest=get(url,html=True)
    race=((raw.get("props") or {}).get("pageProps") or {}).get("race") or {}
    head=race.get("race_summary") or {}
    if str((head.get("race_summary_reference") or {}).get("id") or "")!=str(s["race_id"]) or str(head.get("date") or "")[:10]!=day:
        raise SourceFailure("Result race identity or date mismatch: "+url)
    stage=str(head.get("race_stage") or "").upper()
    if stage in {"ABANDONED","RACEVOID","VOID"}:return {"outcome":"VOID","source_url":url,"stage":stage}
    if stage!="WEIGHEDIN":return {"outcome":"PENDING","source_url":url,"reason":"Not officially weighed in: "+stage}
    rides=[x for x in race.get("rides",[]) if isinstance(x,dict)]
    if not any(str(x.get("finish_position"))=="1" for x in rides):
        return {"outcome":"PENDING","source_url":url,"reason":"Weighed-in page missing official winner"}
    selected=[x for x in rides if str(((x.get("horse") or {}).get("horse_reference") or {}).get("id"))==str(s["horse_id"])]
    if len(selected)!=1:return {"outcome":"PENDING","reason":"Horse identity not confirmed in result","source_url":url}
    ride=selected[0]
    if nonrunner(ride):return {"outcome":"VOID","reason":"Non-runner","source_url":url}
    raw_pos=ride.get("amended_position") if ride.get("amended_position") not in (None,"") else ride.get("finish_position")
    try:position=int(raw_pos)
    except (ValueError,TypeError):position=0
    casualty=ride.get("casualty") or {}
    if position<=0 and not casualty.get("reason"):
        return {"outcome":"PENDING","reason":"Unknown final placing/nonfinish","source_url":url}
    return {"outcome":"WIN" if position==1 else "LOSS","position":position or None,
        "nonfinish_reason":casualty.get("reason"),"source_url":url,"stage":stage,
        "payload_sha256":digest,"verified_at_uk":iso(now_uk()),
        "betfair_bsp":None,"bsp_note":"No verified Betfair BSP"}

def picks_list():
    return [read(p) for p in sorted(BASE.glob("????-??-??-picks.json"))]

def results_map():
    results={}
    for path in sorted((BASE/"results").glob("*/*.json")):
        event=read(path)
        for row in event["results"]:
            key=(event["date"],str(row["race_id"]),str(row["horse_id"]))
            if row["outcome"] in {"WIN","LOSS","VOID"}:
                if key in results and results[key]["outcome"] in {"WIN","LOSS"} and results[key]["outcome"]!=row["outcome"]:
                    raise SourceFailure("Conflicting settled outcomes: "+str(key))
                results[key]=row
            elif key not in results:results[key]=row
    return results

def replay(picks,results):
    summary={}
    for portfolio in ("NAP-only","Top-3"):
        ordered=[]
        for record in picks:
            for horse in record["selections"]:
                if portfolio=="NAP-only" and horse["rank"]!=1:continue
                key=(record["date"],str(horse["race_id"]),str(horse["horse_id"]))
                ordered.append((horse,record["date"],results.get(key,{"outcome":"PENDING"})))
        ordered.sort(key=lambda x:(x[0]["off_datetime_uk"],x[0]["race_id"],x[0]["horse_id"]))
        summary[portfolio]={}
        for method in ("flat","x1.5_cap30","x2_cap40"):
            bank=Decimal(900);nextstake=Decimal(10);peak=bank;drawdown=Decimal(0)
            loss_streak=max_streak=win=loss=0;staked=Decimal(0);blocked=False;ledger=[]
            for h,day,res in ordered:
                label=f"{day}/{h['race_id']}/{h['horse_id']}"
                outcome=res["outcome"]
                quote=h["reference_price_decimal"] if h["price_eligible"] else None
                if quote is None:
                    ledger.append({"key":label,"status":"FORECAST_ONLY_UNPRICED","outcome":outcome});continue
                if outcome=="VOID":
                    ledger.append({"key":label,"status":"VOID"});continue
                if outcome not in {"WIN","LOSS"} or blocked:
                    blocked=True;ledger.append({"key":label,"status":"PENDING_EARLIER_RESULT","outcome":outcome});continue
                if bank<nextstake:
                    blocked=True;ledger.append({"key":label,"status":"INSUFFICIENT_BANK"});continue
                stake=nextstake
                profit=money(stake*(Decimal(str(quote))-1)*Decimal(".95")) if outcome=="WIN" else -stake
                bank=money(bank+profit);staked+=stake
                if outcome=="WIN":win+=1;loss_streak=0
                else:loss+=1;loss_streak+=1;max_streak=max(max_streak,loss_streak)
                if method=="flat":nextstake=Decimal(10)
                elif method=="x1.5_cap30":nextstake=min(Decimal(30),Decimal(10)*(Decimal("1.5")**loss_streak))
                else:nextstake=min(Decimal(40),Decimal(10)*(Decimal(2)**loss_streak))
                peak=max(peak,bank);drawdown=max(drawdown,peak-bank)
                ledger.append({"key":label,"horse":h["horse"],"outcome":outcome,
                    "stake_gbp":str(stake),"reference_price":quote,
                    "pnl_gbp":str(profit),"bank_after_gbp":str(bank)})
            profit=bank-Decimal(900)
            summary[portfolio][method]={"bank_gbp":str(bank),"pnl_gbp":str(profit),
                "wins":win,"losses":loss,"total_staked_gbp":str(staked),
                "roi_pct":str(money(100*profit/staked)) if staked else None,
                "max_drawdown_gbp":str(drawdown),"longest_losing_streak":max_streak,
                "next_stake_gbp":str(money(nextstake)),"progression_blocked":blocked,"ledger":ledger}
    return summary

def evening(now):
    observations=[]
    records=picks_list()
    results=results_map()
    for record in records:
        day=record["date"]
        delta=(now.date()-datetime.fromisoformat(day).date()).days
        if delta<0 or delta>7:continue
        for horse in record["selections"]:
            key=(day,str(horse["race_id"]),str(horse["horse_id"]))
            if results.get(key,{}).get("outcome") in {"WIN","LOSS","VOID"}:continue
            off=off_time(day,horse["race_time_uk"])
            if not off or off>now-timedelta(minutes=35):continue
            try:result=result_for(horse,day)
            except Exception as e:result={"outcome":"PENDING","reason":str(e)[:300]}
            observations.append((day,{"race_id":horse["race_id"],"horse_id":horse["horse_id"],
                 "horse":horse["horse"],**result}))
    for day in sorted({d for d,_ in observations}):
        dated=[r for d,r in observations if d==day]
        timestamp=now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H%M%S%fZ")
        write_once(BASE/"results"/day/(timestamp+".json"),
          {"date":day,"reconciled_at_uk":iso(now),"results":dated})
    replay_results=results_map()
    unresolved=sum(1 for p in records for h in p["selections"]
        if replay_results.get((p["date"],str(h["race_id"]),str(h["horse_id"])),{}).get("outcome") not in {"WIN","LOSS","VOID"})
    state={"source_system":"independent-shadow-v1","as_of_uk":iso(now),
        "unresolved":unresolved,"portfolios":replay(records,replay_results),
        "warning":"Hypothetical bookmaker reference prices, 5% illustrative commission; NO matched Betfair bets or verified BSP"}
    BASE.mkdir(parents=True,exist_ok=True)
    (BASE/"status.json").write_text(json.dumps(state,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    LOG.info("Evening: %d new results; %d still unresolved",len(observations),unresolved)

def smoke(now):
    cards,_,_=listing(now.date().isoformat())
    LOG.info("Smoke: got %d racecards",len(cards))
    raw,_=get(cards[0]["url"],html=True)
    race=((raw.get("props") or {}).get("pageProps") or {}).get("race") or {}
    head=race.get("race_summary") or {}
    if str((head.get("race_summary_reference") or {}).get("id"))!=cards[0]["race_id"] or not race.get("rides"):
        raise SourceFailure("Racecard detail smoke test failed")
    LOG.info("Source smoke succeeded: %s, %s runners",cards[0]["race_id"],len(race["rides"]))

def main(argv=None):
    ap=argparse.ArgumentParser()
    ap.add_argument("mode",choices=["smoke","morning","evening"])
    args=ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO,format="%(levelname)s %(message)s")
    now=now_uk()
    if args.mode=="smoke":smoke(now)
    elif args.mode=="morning":morning(now)
    else:evening(now)

if __name__=="__main__":
    try:main()
    except Exception:
        LOG.exception("Paper-only processor failed, will retry on next independent schedule")
        sys.exit(1)
