"""Read-only market-making feasibility pilot inspired by Hummingbot concepts.
Not Hummingbot itself. Does not place orders or claim fill probability."""
import json,datetime,urllib.request
from decimal import Decimal
D=Decimal
SYMBOLS=["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT"]
FEE=D("0.001")
CAPITAL=D("20")
def get(symbol):
    url="https://data-api.binance.vision/api/v3/depth?symbol="+symbol+"&limit=20"
    req=urllib.request.Request(url,headers={"User-Agent":"MPTM-paper-research/1.0"})
    with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
def run():
    results=[]; errors=[]
    for symbol in SYMBOLS:
        try:
            book=get(symbol)
            bid,bidqty=map(D,book["bids"][0])
            ask,askqty=map(D,book["asks"][0])
            mid=(bid+ask)/2
            spread=(ask/bid-1)*100
            roundtrip=(ask*(1-FEE)/(bid*(1+FEE))-1)*100
            results.append({"symbol":symbol,"bid":str(bid),"ask":str(ask),
                "spread_pct":str(round(spread,6)),
                "maker_roundtrip_pct_if_both_filled":str(round(roundtrip,6)),
                "top_bid_notional":str(round(bid*bidqty,3)),
                "top_ask_notional":str(round(ask*askqty,3)),
                "capital_per_side_usdt":str(CAPITAL/2),
                "caveat":"No maker queue position, fills, inventory, rebates, volatility, or account eligibility modeled"})
        except Exception as exc:errors.append({"symbol":symbol,"error":str(exc)})
    output={"timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "experiment":"market making spread feasibility, not paper-traded fills",
      "fee_per_leg_assumption":str(FEE),"virtual_capital_usdt":str(CAPITAL),
      "results":results,"errors":errors,
      "verified_profit":None}
    with open("market_making_results.json","w") as f:json.dump(output,f,indent=2)
    print(json.dumps(output,indent=2))
    if not results:raise RuntimeError("No market data; test failed")
if __name__=="__main__":run()
