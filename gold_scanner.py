"""Gold token spot arbitrage research. Public order books only; NO orders."""
import datetime,json,urllib.request,sys
from decimal import Decimal
D=Decimal
ASSETS=["PAXG","XAUT"]
CAPITALS=[D("10"),D("50"),D("100")]
FEES={"Binance":D("0.001"),"OKX":D("0.001"),"Bitget":D("0.001")}
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"MPTM-Gold-Research/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=18) as resp:return json.load(resp)
def depth(venue,asset):
    if venue=="Binance":
        d=get("https://data-api.binance.vision/api/v3/depth?symbol="+asset+"USDT&limit=20")
        return d["asks"],d["bids"]
    if venue=="OKX":
        d=get("https://www.okx.com/api/v5/market/books?instId="+asset+"-USDT&sz=20")
        if d.get("code")!="0" or not d.get("data"):raise ValueError(str(d.get("msg","no data")))
        return d["data"][0]["asks"],d["data"][0]["bids"]
    if venue=="Bitget":
        d=get("https://api.bitget.com/api/v3/market/orderbook?category=SPOT&symbol="+asset+"USDT&limit=20")
        if d.get("code")!="00000" or not d.get("data"):raise ValueError(str(d.get("msg","no data")))
        return d["data"]["a"],d["data"]["b"]
    raise ValueError("unsupported venue")
def buy_with_quote(asks,quote):
    remaining=quote;qty=D("0")
    for level in asks:
        price,available=D(str(level[0])),D(str(level[1]))
        if price<=0 or available<=0:continue
        take=min(available,remaining/price)
        qty+=take;remaining-=take*price
        if remaining<=D("0.000000001"):break
    return qty,remaining
def sell_base(bids,qty):
    remaining=qty;proceeds=D("0")
    for level in bids:
        price,available=D(str(level[0])),D(str(level[1]))
        if price<=0 or available<=0:continue
        take=min(available,remaining)
        proceeds+=take*price;remaining-=take
        if remaining<=D("0.000000000001"):break
    return proceeds,remaining
def main():
    books={};errors=[];rows=[]
    for asset in ASSETS:
        for venue in FEES:
            try:
                asks,bids=depth(venue,asset)
                if not asks or not bids:raise ValueError("empty order book")
                books[(asset,venue)]=(asks,bids)
            except Exception as exc:errors.append({"asset":asset,"venue":venue,"error":str(exc)[:180]})
    for asset in ASSETS:
        for buy in FEES:
            for sell in FEES:
                if buy==sell or (asset,buy) not in books or (asset,sell) not in books:continue
                asks=books[(asset,buy)][0];bids=books[(asset,sell)][1]
                for capital in CAPITALS:
                    bought,unused=buy_with_quote(asks,capital)
                    if unused>D("0.00001"):continue
                    transferable=bought*(1-FEES[buy])
                    received,unsold=sell_base(bids,transferable)
                    if unsold>D("0.00000001"):continue
                    net=received*(1-FEES[sell])-capital
                    rows.append({"asset":asset,"buy":buy,"sell":sell,"capital_usdt":str(capital),
                        "estimated_net_before_transfer_usdt":str(round(net,6)),
                        "estimated_pct":str(round(net/capital*100,5)),
                        "depth_20_levels_passed":True,"executable":False})
    report={"checked_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "method":"Sequential public depth snapshots, up to 20 levels each",
        "assets":ASSETS,"venues":list(FEES),"fee_assumptions":{k:str(v) for k,v in FEES.items()},
        "successful_books":[{"asset":a,"venue":v} for a,v in books],
        "errors":errors,"scenarios":len(rows),
        "positive_indicative":sum(D(r["estimated_net_before_transfer_usdt"])>0 for r in rows),
        "best":sorted(rows,key=lambda r:D(r["estimated_pct"]),reverse=True)[:15],
        "verified_executable_profit":None,
        "limitations":"No synchronized executable quotes, account-specific fees, token transfer costs, network compatibility, custody, minimum order size, precision, FX or Turkey eligibility validation. Requires prefunded accounts; PAXG and XAUT are different assets."}
    with open("gold_results.json","w",encoding="utf-8") as f:json.dump(report,f,indent=2)
    print(json.dumps(report,indent=2))
    if len(rows)==0:sys.exit("NO_COMPARABLE_GOLD_MARKETS")
if __name__=="__main__":main()
