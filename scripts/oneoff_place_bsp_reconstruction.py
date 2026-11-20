"""ONE-OFF retrospective research: third-party-reported Betfair PLACE BSP.

Original official Betfair free CSV endpoint returned HTTP 403 from GitHub Actions
on 2026-11-20. This uses a third-party archive, not independently Betfair-verified
price ticks. No bet placement; never edits old paper banks or locked picks.
"""
from __future__ import annotations
import csv, html, json, re, sys, urllib.request
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

BASE=Path("strongest-horse-back-paper")
DEST=BASE/"place-bsp-retrospective"
DATES=("2026-11-16","2026-11-18","2026-11-19","2026-11-20")
TRACKS={("2026-11-16","Plumpton"):"plumpton",
        ("2026-11-16","Wolverhampton (AW)"):"wolverhampton",
        ("2026-11-18","Hexham"):"hexham",
        ("2026-11-18","Ffos Las"):"ffos-las",
        ("2026-11-19","Newcastle (AW)"):"newcastle-aw",
        ("2026-11-20","Ascot"):"ascot"}
def norm(value):
    return re.sub(r"[^a-z0-9]","",html.unescape(str(value)).lower())
def clean(value):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",str(value)))).strip()
def money(value):
    return Decimal(str(value)).quantize(Decimal(".01"),rounding=ROUND_HALF_UP)
def fetch(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; ResearchOnly; +https://github.com/)","Accept":"text/html"})
    with urllib.request.urlopen(req,timeout=40) as resp:
        if resp.status!=200:raise ValueError(f"HTTP {resp.status}")
        return resp.read(1_000_000).decode("utf-8","replace")
def pages():
    output={}
    for (day,track),slug in TRACKS.items():
        url=f"https://stablewhispers.co.uk/fast-results/{day}/{slug}/"
        try:
            body=fetch(url)
            if day not in body:raise ValueError("Date not found on archived page")
            output[(day,track)]=(url,body)
            print("SOURCE_OK",day,track,len(body),url)
        except Exception as e:
            print("SOURCE_FAILED",day,track,type(e).__name__,str(e)[:250])
    return output

def parse_race(page_html,day,track,time,horse):
    chunks=page_html.split('<div class="swr-race">')
    matches=[]
    for chunk in chunks[1:]:
        h2=re.search(r'<h2 class="swr-race-head"[^>]*>(.*?)</h2>',chunk,re.S)
        if not h2:continue
        head=h2.group(1)
        t=re.search(r'<span class="swr-time">(.*?)</span>',head,re.S)
        if not t or clean(t.group(1))!=time:continue
        n=re.search(r'<span class="swr-places">(\d+) ran</span>',head,re.I)
        if not n:raise ValueError("Missing starter count for target race")
        starters=int(n.group(1))
        title=re.search(r'<span class="swr-rname">(.*?)</span>',head,re.S)
        title=clean(title.group(1)) if title else ""
        table=re.search(r'<table class="swr-table">(.*?)</table>',chunk,re.S)
        if not table:raise ValueError("Missing runner/odds table")
        raw=table.group(1)
        headers=[clean(x) for x in re.findall(r'<th[^>]*>(.*?)</th>',raw,re.S)]
        rows=[]
        for tr in re.findall(r'<tr class="swr-row[^"]*"[^>]*>(.*?)</tr>',raw,re.S):
            cells=re.findall(r'<td[^>]*>(.*?)</td>',tr,re.S)
            if len(cells)!=len(headers):continue
            d=dict(zip(headers,[clean(x) for x in cells]))
            name=re.sub(r'^\d+\s+','',d.get("Horse",""))
            if norm(name)==norm(horse):
                matches.append((starters,title,headers,d))
    if len(matches)!=1:
        raise ValueError(f"Found {len(matches)} unique runner matches (required 1) for {day} {track} {time} {horse}")
    starters,title,headers,row=matches[0]
    pos_match=re.match(r"^\d+",row.get("Pos",""))
    if not pos_match:raise ValueError("Could not confirm official finishing position")
    position=int(pos_match.group())
    handicap=bool(re.search(r"\bhandicap\b|\bhcap\b",title,re.I))
    market=("Top 4" if starters>=16 and handicap else "Top 3" if starters>=8 else "Top 2" if starters>=5 else None)
    data={"race_name":title,"starters":starters,"position":position,
        "market_label":market,"price_decimal":None,"status":None,
        "bookmaker_sp":row.get("SP"),"win_bsp_third_party":row.get("Win BSP")}
    if market is None:
        data["status"]="INELIGIBLE_FEWER_THAN_5_STARTERS"
        return data
    if market not in headers or not row.get(market):
        data["status"]="PRICE_UNAVAILABLE_IN_THIRD_PARTY_ARCHIVE"
        return data
    try:price=Decimal(row[market].replace(",",""))
    except Exception:raise ValueError(f"Unparseable {market} decimal quote")
    if not price.is_finite() or price<=1 or price>=1001:raise ValueError("Invalid or non-traded PLACE BSP")
    placed=position<=int(market.split()[1])
    pnl=money(Decimal("10")*(price-1)*Decimal(".95")) if placed else Decimal("-10.00")
    data.update({"status":"PLACED" if placed else "UNPLACED",
      "price_decimal":str(price),"pnl_gbp":str(pnl),
      "market_term_method":"Inferred from starters/handicap in third-party page; not Betfair official market ID",
      "commission_assumption_pct":5})
    return data

def load_picks():
    selections=[]
    for day in DATES:
        doc=BASE/(day+"-picks.json")
        obj=json.loads(doc.read_text("utf8"))
        if obj.get("date")!=day:raise ValueError(f"Date mismatch in {doc}")
        for horse in obj.get("selections",[]):
            if (day,horse["racecourse"]) not in TRACKS:raise ValueError("Unknown course match")
            selections.append({"date":day,"rank":horse["rank"],"horse":horse["horse"],
                "racecourse":horse["racecourse"],"race_time_uk":horse["race_time_uk"],
                "original_pick_timestamp_uk":obj["prediction_timestamp_uk"],
                "original_win_reference_decimal":horse.get("reference_price_decimal")})
    if len(selections)!=11:raise ValueError("Expected exactly 11 historical locked horses")
    return selections

def main():
    s=load_picks()
    sources=pages()
    rows=[]
    for pick in s:
        row=dict(pick)
        key=(pick["date"],pick["racecourse"])
        if key not in sources:
            row["status"]="SOURCE_UNAVAILABLE"
        else:
            url,body=sources[key]
            row["source_url"]=url
            try:row.update(parse_race(body,pick["date"],pick["racecourse"],pick["race_time_uk"],pick["horse"]))
            except Exception as e:row.update({"status":"MATCH_FAILED","error":str(e)})
        print("SELECTION",json.dumps(row,ensure_ascii=False))
        rows.append(row)
    reports={}
    for grp in ["NAP-only","Top-three"]:
        group=[r for r in rows if grp=="Top-three" or r["rank"]==1]
        settled=[r for r in group if r["status"] in ("PLACED","UNPLACED")]
        profit=sum((Decimal(r["pnl_gbp"]) for r in settled),Decimal("0"))
        reports[grp]={"original_picks":len(group),"priced_settled":len(settled),
            "placed":sum(r["status"]=="PLACED" for r in settled),
            "unplaced":sum(r["status"]=="UNPLACED" for r in settled),
            "omitted":len(group)-len(settled),
            "total_stakes_gbp":str(money(Decimal(10)*len(settled))),
            "pnl_gbp":str(money(profit)),
            "bank_if_started_at_900_gbp":str(money(Decimal(900)+profit)),
            "roi_pct":str(money(Decimal(100)*profit/(Decimal(10)*len(settled)))) if settled else None}
    output={"study":"ONE-OFF PLACE BSP retrospective from 11 original locked picks",
        "research_dates":DATES,
        "original_picks_count":11,
        "source":"https://stablewhispers.co.uk/fast-results/",
        "source_grade":"THIRD_PARTY_UNVERIFIED",
        "why_not_official":"Betfair promo Place CSV returned HTTP 403 from GitHub Actions for all four dates",
        "market_and_price_caveats":"Top 2/3/4 place BSP reported by third-party site; correct named market chosen by actual starters and race type, not verified Betfair market IDs. Not bookmaker each-way fractions. Does not establish executable matched bet or authenticated Betfair SP settlement.",
        "stake_per_selection_gbp":10,
        "commission_assumption": "5% of positive theoretical net profit for each race",
        "retrospective_not_forward":True,
        "original_win_and_place_forward_ledgers_unchanged":True,
        "portfolios":reports,"selections":rows}
    DEST.mkdir(parents=True,exist_ok=True)
    (DEST/"2026-11-16_to_2026-11-20-third-party-place-bsp.json").write_text(
        json.dumps(output,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    fields=["date","rank","horse","racecourse","race_time_uk","starters","position","market_label",
        "price_decimal","status","pnl_gbp","source_url"]
    with (DEST/"2026-11-16_to_2026-11-20-third-party-place-bsp.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(rows)
    print("SUMMARY",json.dumps(reports,ensure_ascii=False))
    print("CAUTION Source = third party; official Betfair CSV blocked. No claim of verified actual Betfair Place market or executable outcomes.")
    if any(r["status"] in ("MATCH_FAILED","SOURCE_UNAVAILABLE") for r in rows):
        print("WARNING partial archive match; never treat as fully verified historical backtest.")

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("BACKTEST_FATAL",type(exc).__name__,str(exc),file=sys.stderr)
        raise
