"""MPTM cross-market v0.1: read-only public CEX quote comparison."""
import datetime
import json
import urllib.request
from decimal import Decimal

D=Decimal
ASSETS=["BTC","ETH","SOL","XRP","DOGE","ADA","LINK","AVAX"]
AMOUNTS=[D("10"),D("50"),D("100")]
# Illustrative fees, not account-specific or verified.
FEES={"OKX":D("0.001"),"Bybit":D("0.001"),"Kraken":D("0.004"),"Coinbase":D("0.006")}
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"MPTM-Research/0.1","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=16) as resp:
        return json.load(resp)
def okx(asset):
    x=get("https://www.okx.com/api/v5/market/ticker?instId="+asset+"-USDT")
    if x.get("code")!="0" or not x.get("data"): raise ValueError(str(x.get("msg","missing ticker")))
    y=x["data"][0]
    return {"bid":D(y["bidPx"]),"ask":D(y["askPx"]),"bid_qty":D(y["bidSz"]),"ask_qty":D(y["askSz"])}
def bybit(asset):
    x=get("https://api.bybit.com/v5/market/tickers?category=spot&symbol="+asset+"USDT")
    if x.get("retCode")!=0 or not x.get("result",{}).get("list"): raise ValueError(str(x.get("retMsg","missing ticker")))
    y=x["result"]["list"][0]
    return {"bid":D(y["bid1Price"]),"ask":D(y["ask1Price"]),"bid_qty":D(y["bid1Size"]),"ask_qty":D(y["ask1Size"])}
def main():
    all_rows=[]; errors=[]
    for asset in ASSETS:
        books={}
        for name,func in [("OKX",okx),("Bybit",bybit)]:
            try:
                b=func(asset)
                if b["bid"]>0 and b["ask"]>0: books[name]=b
            except Exception as exc:
                errors.append({"asset":asset,"exchange":name,"error":str(exc)[:220]})
        for buy_name,buy in books.items():
            for sell_name,sell in books.items():
                if buy_name==sell_name: continue
                for amount in AMOUNTS:
                    qty=amount/buy["ask"]
                    net=qty*sell["bid"]*(1-FEES[buy_name])*(1-FEES[sell_name])-amount
                    all_rows.append({"asset":asset,"buy":buy_name,"sell":sell_name,"amount_usdt":str(amount),
                                     "buy_ask":str(buy["ask"]),"sell_bid":str(sell["bid"]),
                                     "net_before_transfers_usdt":str(round(net,6)),
                                     "net_pct":str(round(100*net/amount,5)),
                                     "top_book_quantity_sufficient":qty<=buy["ask_qty"] and qty<=sell["bid_qty"]})
    result={"timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "mode":"read-only, sequential public top-of-book observations",
            "fee_assumptions":{k:str(v) for k,v in FEES.items()},
            "scenarios":len(all_rows),"positive_indicative":sum(D(r["net_pct"])>0 for r in all_rows),
            "best":sorted(all_rows,key=lambda x:D(x["net_pct"]),reverse=True)[:12],
            "errors":errors,"verified_executable_profit":None,
            "limitations":"Not a trade signal. Both venues require prefunded inventory; fee tiers, deposit/withdrawal, transfers, order minimums, regional eligibility, latency and full depth unverified."}
    with open("cross_market_results.json","w") as f: json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
if __name__=="__main__": main()
