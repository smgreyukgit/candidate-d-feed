"""Offline tests for the separate hypothetical PLACE comparison."""
import unittest
from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo
from independent_horse import place_shadow as p

D="2026-11-21"
def fake_race(starters=8,handicap=False,horse_position=3):
    rides=[]
    for i in range(1,starters+1):
        rides.append({"horse":{"name":"Chosen" if i==1 else f"Runner {i}"},
            "finish_position":horse_position if i==1 else (1 if i==2 else i),
            "ride_status":"RUNNER"})
    # Ensure the official field has one valid winner and non-duplicate placing
    rides[1]["finish_position"]=1
    return {"props":{"pageProps":{"race":{"race_summary":{"race_summary_reference":{"id":"123"},
        "date":D,"race_stage":"WEIGHEDIN","has_handicap":handicap},"rides":rides}}}}

class TestPlace(unittest.TestCase):
    def setUp(self):
        self.pick={"horse":"Chosen","racecourse":"Ascot","race_time_uk":"14:30",
                   "reference_price_decimal":2.75}
        self.card={"race_id":"123","date":D,"result_url":"https://example.test/r",
                   "course":"Ascot","off":"14:30"}
    def test_terms(self):
        self.assertIsNone(p.place_terms(4,False))
        self.assertEqual(p.place_terms(7,False),{"places":2,"fraction":"0.25","basis":"5-7 starters"})
        self.assertEqual(p.place_terms(8,False)["places"],3)
        self.assertEqual(p.place_terms(12,False)["fraction"],"0.20")
        self.assertEqual(p.place_terms(12,True)["fraction"],"0.25")
        self.assertEqual(p.place_terms(16,True)["places"],4)
        self.assertEqual(p.place_terms(16,False)["places"],3)
    def test_place_payout(self):
        with patch.object(p,"get",return_value=(fake_race(8,False,3),"abcdef")):
            r=p.result(self.pick,D,self.card)
        self.assertEqual(r["status"],"PLACED")
        self.assertEqual(r["places_paid"],3)
        self.assertEqual(r["illustrative_place_reference_decimal"],"1.3500")
        self.assertEqual(r["pnl_gbp"],"3.33")
    def test_seven_runners_third_is_loss(self):
        with patch.object(p,"get",return_value=(fake_race(7,False,3),"abcdef")):
            r=p.result(self.pick,D,self.card)
        self.assertEqual(r["status"],"UNPLACED")
        self.assertEqual(r["pnl_gbp"],"-10")
    def test_race_identity_rejected(self):
        bad=fake_race()
        bad["props"]["pageProps"]["race"]["race_summary"]["race_summary_reference"]["id"]="oops"
        with patch.object(p,"get",return_value=(bad,"abcdef")):
            with self.assertRaises(ValueError):p.result(self.pick,D,self.card)
    def test_post_off_selection_rejected(self):
        d={"date":D,"prediction_timestamp_uk":D+"T14:35:00+00:00",
          "selections":[{"horse":"Chosen","rank":1,"racecourse":"Ascot","race_time_uk":"14:30"}]}
        self.assertEqual(p.stamped_picks(d),[])
    def test_matches_race_not_guess(self):
        cards=[self.card,{"race_id":"124","date":D,"result_url":"r",
                          "course":"Ascot","off":"14:40"}]
        self.assertEqual(p.choose_card(self.pick,cards)["race_id"],"123")
    def test_position_and_price_not_blended_with_exchange(self):
        with patch.object(p,"get",return_value=(fake_race(6,False,2),"abcdef")):
            r=p.result(self.pick,D,self.card)
        self.assertEqual(r["status"],"PLACED")
        self.assertEqual(r["fraction"],"0.25")
        self.assertEqual(r["pnl_gbp"],"4.16")
        self.assertNotIn("exchange_price",r)

if __name__=="__main__":unittest.main()
