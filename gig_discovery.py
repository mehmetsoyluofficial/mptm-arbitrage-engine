"""Discover public paid AI-agent gigs; no claims, accounts, wallets or spending."""
import json, datetime, urllib.request
URL="https://jobbi.org/gigs.json"
def main():
    req=urllib.request.Request(URL,headers={"User-Agent":"MPTM-gig-research/1.0","Accept":"application/feed+json, application/json"})
    with urllib.request.urlopen(req,timeout=25) as response:
        feed=json.load(response)
    entries=feed.get("items",[])
    picks=[]
    for item in entries:
        data=item.get("_jobbi",{}) or item.get("jobbi",{}) or {}
        text=" ".join(str(item.get(k,"")) for k in ("title","summary","content_text"))
        if any(word in text.lower() for word in ("deposit to claim","refundable bond","fund a child bounty","buy a subscription")):
            continue
        picks.append({"title":item.get("title"),"url":item.get("url") or item.get("external_url"),
          "summary":str(item.get("summary") or item.get("content_text") or "")[:450],
          "metadata":data})
    out={"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "source":URL,"total_feed_items":len(entries),"review_candidates":picks[:40],
      "note":"Discovery only. Verify escrow, eligibility, deadlines, task scope and payout with original board. No income earned."}
    with open("gig_candidates.json","w",encoding="utf-8") as f:json.dump(out,f,ensure_ascii=False,indent=2)
    print(json.dumps({"checked_utc":out["checked_utc"],"total_feed_items":len(entries),"candidates":len(picks[:40])},indent=2))
    if not entries:raise RuntimeError("Feed empty or schema changed; do not report zero opportunities")
if __name__=="__main__":main()
