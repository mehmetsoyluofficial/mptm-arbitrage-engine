"""MPTM Cross-Exchange v0.1 — read-only Kraken vs Coinbase quote research."""
import datetime
import json
import sys
import urllib.request
from decimal import Decimal

D = Decimal
ASSETS = ["BTC", "ETH", "SOL", "ADA", "XRP", "DOGE", "LTC", "LINK", "AVAX"]
CAPITALS = [D("10"), D("50"), D("100")]
# Illustrative fee assumptions; account-specific fees and transfer costs unknown.
FEE_KRAKEN = D("0.004")
FEE_COINBASE = D("0.006")
URL_KRAKEN = "https://api.kraken.com/0/public/Depth?pair={pair}&count=20"
URL_COINBASE = "https://api.exchange.coinbase.com/products/{pair}/book?level=2"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent":"MPTM-Research/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=15) as response:
        return json.load(response)

def book_kraken(asset):
    pair = ("XBT" if asset == "BTC" else asset) + "USD"
    data = fetch(URL_KRAKEN.format(pair=pair))
    if data.get("error"):
        raise ValueError(str(data["error"]))
    book = next(iter(data["result"].values()))
    return {"ask":D(book["asks"][0][0]),"ask_qty":D(book["asks"][0][1]),
            "bid":D(book["bids"][0][0]),"bid_qty":D(book["bids"][0][1])}

def book_coinbase(asset):
    data = fetch(URL_COINBASE.format(pair=asset+"-USD"))
    return {"ask":D(data["asks"][0][0]),"ask_qty":D(data["asks"][0][1]),
            "bid":D(data["bids"][0][0]),"bid_qty":D(data["bids"][0][1])}

def compare(asset,buy_name,buy,sell_name,sell,capital):
    quantity = capital / buy["ask"]
    gross = quantity * sell["bid"]
    fee_buy = FEE_KRAKEN if buy_name=="Kraken" else FEE_COINBASE
    fee_sell = FEE_KRAKEN if sell_name=="Kraken" else FEE_COINBASE
    net = gross*(1-fee_buy)*(1-fee_sell)-capital
    top_liquidity = quantity <= buy["ask_qty"] and quantity <= sell["bid_qty"]
    return {"asset":asset,"buy_at":buy_name,"sell_at":sell_name,
            "capital_usd":str(capital),"buy_ask":str(buy["ask"]),"sell_bid":str(sell["bid"]),
            "estimated_net_usd_before_transfer":str(round(net,6)),
            "estimated_net_pct_before_transfer":str(round(net/capital*100,5)),
            "top_level_quantity_sufficient":top_liquidity,
            "status":"RESEARCH_ONLY_NOT_EXECUTABLE"}

def main():
    records,errors = [],[]
    for asset in ASSETS:
        try:
            k=book_kraken(asset)
            c=book_coinbase(asset)
            for capital in CAPITALS:
                records.append(compare(asset,"Kraken",k,"Coinbase",c,capital))
                records.append(compare(asset,"Coinbase",c,"Kraken",k,capital))
        except Exception as exc:
            errors.append({"asset":asset,"error":str(exc)})
    output={
        "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "method":"sequential top-of-book REST snapshots; not synchronized",
        "fees_assumed":{"Kraken":"0.4%","Coinbase":"0.6%"},
        "limitations":"USD inventory required on both exchanges for immediate execution; transfer, FX, withdrawal, deposit, minimum orders, jurisdiction, account fees and slippage unverified.",
        "scenarios":len(records),"positive_indicative":sum(D(r["estimated_net_usd_before_transfer"])>0 for r in records),
        "top_results":sorted(records,key=lambda r:D(r["estimated_net_pct_before_transfer"]),reverse=True)[:15],
        "errors":errors,"verified_executable_profit":None}
    with open("cross_exchange_results.json","w") as f:
        json.dump(output,f,indent=2)
    print(json.dumps(output,indent=2))
    if not records:
        sys.exit(2)

if __name__=="__main__":
    main()
