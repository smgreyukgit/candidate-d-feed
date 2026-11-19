"""No network and no real bets: deterministic regression tests for the shadow runner."""
import tempfile, unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
from independent_horse import runner as h

D="2026-11-20"
UTC=ZoneInfo("Europe/London")

def card(result=False):
    rides=[]
    for i,form in enumerate(("22311","55432","8P987","45623"),1):
        rides.append({"horse":{"name":f"Horse {i}","horse_reference":{"id":i},
                "formsummary":{"display_text":form},"last_ran_days":18},
            "ride_status":"RUNNER","official_rating":110-i,
            "trainer":{"name":"Trainer"},"jockey":{"name":"Rider"},
            "bookmakerOdds":[{"fractionalOdds":"6/4","bookmaker":{"name":"Test bookmaker"},"bestOdds":True}],
            "finish_position":1 if i==1 else i})
    return {"props":{"pageProps":{"race":{"race_summary":{
        "race_summary_reference":{"id":"123"},"date":D,"time":"13:45",
        "name":"Test","race_stage":"WEIGHEDIN" if result else "CARD"},
        "rides":rides}}}}

class TestHorseShadow(unittest.TestCase):
    def test_price(self):
        self.assertEqual(h.odds("6/4"),2.5)
        self.assertEqual(h.odds("11/10f"),2.1)
        self.assertIsNone(h.odds("not available"))
        self.assertEqual(h.price_of({"bookmakerOdds":[{"fractionalOdds":"6/4"}]})[0],2.5)
        self.assertIsNone(h.price_of({"betting":{"current_odds":"6/4"}})[0])

    def test_form_and_timing(self):
        self.assertEqual(h.form_digits("2P-1F3"),[2,10,1,10,3])
        self.assertEqual(h.off_time(D,"13:45").hour,13)
        self.assertIsNone(h.off_time(D,"unknown"))

    def test_source_identity_and_runner(self):
        c={"date":D,"off":"13:45","race_id":"123","url":"https://example.com/card",
           "name":"Test","course":"Hexham","result_url":"https://example.com/results"}
        with patch.object(h,"get",return_value=(card(), "a"*64)):
            best=h.race_leader(c,datetime(2026,11,20,9,15,tzinfo=UTC))
        self.assertEqual(best["horse"],"Horse 1")
        self.assertEqual(best["reference_price_decimal"],2.5)
        self.assertEqual(best["race_id"],"123")

    def test_result_only_weighed_in(self):
        s={"race_id":"123","horse_id":"1","result_url":"https://example.com/results"}
        with patch.object(h,"get",return_value=(card(True),"a"*64)):
            self.assertEqual(h.result_for(s,D)["outcome"],"WIN")
        with patch.object(h,"get",return_value=(card(False),"a"*64)):
            self.assertEqual(h.result_for(s,D)["outcome"],"PENDING")

    def test_replay_chronology_and_commission(self):
        selections=[
            {"rank":2,"horse":"A","race_id":"1","horse_id":"1","off_datetime_uk":D+"T12:00:00+00:00",
             "reference_price_decimal":2,"price_eligible":True},
            {"rank":1,"horse":"B","race_id":"2","horse_id":"2","off_datetime_uk":D+"T14:00:00+00:00",
             "reference_price_decimal":3,"price_eligible":True}]
        bets=[{"date":D,"selections":selections}]
        res={(D,"1","1"):{"outcome":"LOSS"},(D,"2","2"):{"outcome":"WIN"}}
        r=h.replay(bets,res)
        self.assertEqual(r["NAP-only"]["flat"]["bank_gbp"],"919.00")
        self.assertEqual(r["Top-3"]["flat"]["bank_gbp"],"909.00")
        self.assertEqual(r["Top-3"]["x2_cap40"]["bank_gbp"],"928.00")

    def test_pending_blocks_subsequent_bets(self):
        selections=[
            {"rank":1,"horse":"A","race_id":"1","horse_id":"1","off_datetime_uk":D+"T12:00:00+00:00",
             "reference_price_decimal":2,"price_eligible":True},
            {"rank":2,"horse":"B","race_id":"2","horse_id":"2","off_datetime_uk":D+"T14:00:00+00:00",
             "reference_price_decimal":3,"price_eligible":True}]
        r=h.replay([{"date":D,"selections":selections}],{(D,"2","2"):{"outcome":"WIN"}})
        self.assertEqual(r["Top-3"]["flat"]["bank_gbp"],"900")
        self.assertTrue(r["Top-3"]["flat"]["progression_blocked"])

    def test_picks_never_overwritten(self):
        with tempfile.TemporaryDirectory() as path:
            p=Path(path)/"locked.json"
            h.write_once(p,{"pick":"Horse A"})
            with self.assertRaises(FileExistsError):
                h.write_once(p,{"pick":"after-race winner"})
            self.assertEqual(h.read(p)["pick"],"Horse A")

if __name__=="__main__":unittest.main()
