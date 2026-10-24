"""MPTM multi-venue research: OKX, Kraken, Coinbase, separate USD/USDT markets."""
import datetime,json,sys,urllib.request
from decimal import Decimal
D=Decimal
ASSETS=["BTC","ETH","SOL","XRP","ADA","DOGE","LTC","LINK"]
CAPITAL=[D("10"),D("50"),D("100")]
FEES={"OKX":D("0.001"),"Kraken":D("0.004"),"Coinbase":D("0.006")}
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"MPTM-Research/1.1","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=16) as response:return json.load(response)
def okx(asset):
    d=get("https://www.okx.com/api/v5/market/ticker?instId="+asset+"-USDT")
    if d.get("code")!="0" or not d.get("data"):raise ValueError(str(d.get("msg","no data")))
    x=d["data"][0]
    return {"bid":D(x["bidPx"]),"ask":D(x["askPx"]),"bid_qty":D(x["bidSz"]),"ask_qty":D(x["askSz"])}
def kraken(asset,quote):
    pair=("XBT" if asset=="BTC" else asset)+quote
    d=get("https://api.kraken.com/0/public/Depth?pair="+pair+"&count=5")
    if d.get("error"):raise ValueError(str(d["error"]))
    x=next(iter(d["result"].values()))
    return {"bid":D(x["bids"][0][0]),"ask":D(x["asks"][0][0]),"bid_qty":D(x["bids"][0][1]),"ask_qty":D(x["asks"][0][1])}
def coinbase(asset,quote):
    d=get("https://api.exchange.coinbase.com/products/"+asset+"-"+quote+"/book?level=1")
    return {"bid":D(d["bids"][0][0]),"ask":D(d["asks"][0][0]),"bid_qty":D(d["bids"][0][1]),"ask_qty":D(d["asks"][0][1])}
def main():
    quotes={};errors=[];records=[];health={}
    for asset in ASSETS:
        for venue,quote,func in [("OKX","USDT",lambda:okx(asset)),("Kraken","USD",lambda:kraken(asset,"USD")),("Kraken","USDT",lambda:kraken(asset,"USDT")),("Coinbase","USD",lambda:coinbase(asset,"USD")),("Coinbase","USDT",lambda:coinbase(asset,"USDT"))]:
            key=venue+":"+quote
            try:
                b=func()
                if b["bid"]<=0 or b["ask"]<=0:raise ValueError("nonpositive quote")
                quotes[(asset,venue,quote)]=b
                health[key]=health.get(key,0)+1
            except Exception as exc:
                errors.append({"asset":asset,"source":key,"error":str(exc)[:180]})
    for asset in ASSETS:
        for quote in ["USD","USDT"]:
            available=[(venue,b) for (a,venue,q),b in quotes.items() if a==asset and q==quote]
            for buy_name,buy in available:
                for sell_name,sell in available:
                    if buy_name==sell_name:continue
                    for capital in CAPITAL:
                        qty=capital/buy["ask"]
                        net=qty*sell["bid"]*(1-FEES[buy_name])*(1-FEES[sell_name])-capital
                        records.append({"asset":asset,"quote_currency":quote,"buy":buy_name,"sell":sell_name,
                            "capital":str(capital),"net_before_transfers":str(round(net,6)),
                            "net_pct":str(round(net/capital*100,5)),
                            "top_book_quantity_sufficient":qty<=buy["ask_qty"] and qty<=sell["bid_qty"]})
    result={"timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_health":health,"errors":errors,"scenarios":len(records),
        "positive_indicative":sum(D(x["net_pct"])>0 for x in records),
        "best":sorted(records,key=lambda x:D(x["net_pct"]),reverse=True)[:15],
        "fees_assumed":{k:str(v) for k,v in FEES.items()},
        "verified_executable_profit":None,
        "limitations":"USD and USDT are not equated. Sequential non-synchronized quotes, approximate fees, no full depth, FX conversion, withdrawal, inventory, account eligibility or execution validation."}
    with open("multi_venue_results.json","w") as f:json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))
    if not records:sys.exit("NO_VALID_CROSS_VENUE_COMPARISONS")
if __name__=="__main__":main()
