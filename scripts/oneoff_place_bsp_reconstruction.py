"""One-off probe of free Betfair PLACE BSP historical CSV. No bets or journal changes."""
from __future__ import annotations
import csv, io, json, re, urllib.request
from pathlib import Path
from datetime import datetime
BASE=Path("strongest-horse-back-paper")
DATES=["2026-11-16","2026-11-18","2026-11-19","2026-11-20"]
HORSES=["Kamille Au Kanada","Saxophonic","R P McMurphy","Old Park Star","Lord Du Gouet","Diamond Street","Big Money","High Threshold","Current Edition","Power Steering","Push The Limit"]
def normalize(s):
    return re.sub(r"[^a-z0-9]","",str(s).lower())
def fetch(day):
    fn="dwbfpricesukplace"+datetime.fromisoformat(day).strftime("%d%m%Y")+".csv"
    url="https://promo.betfair.com/betfairsp/prices/"+fn
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0","Referer":"https://promo.betfair.com/"})
    with urllib.request.urlopen(req, timeout=35) as r:raw=r.read()
    rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    print("FILE",day,url,"bytes",len(raw),"rows",len(rows))
    print("FIELDS",list(rows[0]) if rows else [])
    print("SAMPLE",json.dumps(rows[:2],ensure_ascii=False)[:2300])
    for name in HORSES:
        found=[x for x in rows if normalize(x.get("SELECTION_NAME",""))==normalize(name)]
        if found:
            print("MATCH",day,name,json.dumps(found,ensure_ascii=False)[:1700])
    return rows
def main():
    for date in DATES:
        try:fetch(date)
        except Exception as e:print("SOURCE_ERROR",date,type(e).__name__,str(e))
if __name__=="__main__":main()
