"""MPTM v0.5: read-only market research with depth and exchange filters."""
import datetime
import json
import sys
import urllib.request
from decimal import Decimal, ROUND_DOWN

API = "https://data-api.binance.vision/api/v3/"
D = Decimal

def fetch(path):
    req = urllib.request.Request(API + path, headers={"User-Agent": "MPTM-research/0.5"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)

def floor_step(value, step):
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step if step > 0 else value

def build(info, books, fee):
    symbols = {s["symbol"]: s for s in info["symbols"] if s["status"] == "TRADING" and s.get("isSpotTradingAllowed", True)}
    edges = {}
    for b in books:
        s = symbols.get(b["symbol"])
        if not s:
            continue
        bid, ask = D(b["bidPrice"]), D(b["askPrice"])
        if bid <= 0 or ask <= 0:
            continue
        base, quote = s["baseAsset"], s["quoteAsset"]
        edges[(base, quote)] = (bid * (1-fee), b["symbol"], "SELL")
        edges[(quote, base)] = ((1/ask) * (1-fee), b["symbol"], "BUY")
    return symbols, edges

def candidates(edges, amount):
    outgoing = {}
    for (a,b), edge in edges.items():
        outgoing.setdefault(a, []).append((b,edge))
    found = []
    for b, e1 in outgoing.get("USDT", []):
        for c, e2 in outgoing.get(b, []):
            if c in ("USDT", b):
                continue
            e3 = edges.get((c,"USDT"))
            if not e3:
                continue
            end = amount * e1[0] * e2[0] * e3[0]
            found.append({"path":["USDT",b,c,"USDT"],"legs":[e1,e2,e3],"indicative_end":end})
    return sorted(found,key=lambda x:x["indicative_end"],reverse=True)

def filter_values(symbol):
    out = {}
    for f in symbol["filters"]:
        if f["filterType"] in ("LOT_SIZE","MARKET_LOT_SIZE","MIN_NOTIONAL","NOTIONAL"):
            out[f["filterType"]] = f
    return out

def simulate(candidate, symbols, fee, amount):
    balance = amount
    steps = []
    for i, (symbol, side) in enumerate((leg[1],leg[2]) for leg in candidate["legs"]):
        spec = symbols[symbol]
        filters = filter_values(spec)
        lot = filters.get("LOT_SIZE",{})
        min_qty = D(lot.get("minQty","0"))
        max_qty = D(lot.get("maxQty","999999999"))
        step = D(lot.get("stepSize","0"))
        orderbook = fetch("depth?symbol=" + symbol + "&limit=100")
        levels = orderbook["asks"] if side == "BUY" else orderbook["bids"]
        remaining = balance
        received = D("0")
        spent_quote = D("0")
        sold_base = D("0")
        for price_text, qty_text in levels:
            price, available = D(price_text), D(qty_text)
            if side == "BUY":
                qty = min(available,remaining/price)
                received += qty
                spent_quote += qty*price
                remaining -= qty*price
            else:
                qty = min(available,remaining)
                received += qty*price
                sold_base += qty
                remaining -= qty
            if remaining <= D("0.00000000001"):
                break
        if remaining > D("0.00000001"):
            return {"status":"REJECT","reason":"Insufficient depth for complete fill","leg":i+1}
        quantity = received if side == "BUY" else sold_base
        rounded = floor_step(quantity,step)
        if rounded < min_qty or rounded > max_qty or rounded != quantity:
            return {"status":"REJECT","reason":"LOT_SIZE/precision or leftover funds","leg":i+1}
        notional = spent_quote if side == "BUY" else received
        minimum = D(filters.get("NOTIONAL",filters.get("MIN_NOTIONAL",{})).get("minNotional","0"))
        if notional < minimum:
            return {"status":"REJECT","reason":"MIN_NOTIONAL","leg":i+1,"notional":str(notional),"minimum":str(minimum)}
        balance = received*(1-fee)
        steps.append({"symbol":symbol,"side":side,"output":str(balance)})
    return {"status":"INDICATIVE_DEPTH_PASS","estimated_end_usdt":str(balance),"estimated_profit_usdt":str(balance-amount),"steps":steps,
            "warning":"Sequential snapshots, not synchronized; fee assumptions, trading permissions, execution, slippage and other filters not fully validated."}

def main():
    amount,fee = D("10"),D("0.001")
    info = fetch("exchangeInfo")
    books = fetch("ticker/bookTicker")
    symbols,edges = build(info,books,fee)
    ranked = candidates(edges,amount)
    positive = [c for c in ranked if c["indicative_end"] > amount]
    checks = []
    for c in positive[:5]:
        item = {"path":c["path"],"pairs":[leg[1] for leg in c["legs"]],"indicative_end_usdt":str(c["indicative_end"])}
        try:
            item["depth_check"] = simulate(c,symbols,fee,amount)
        except Exception as exc:
            item["depth_check"] = {"status":"DATA_UNAVAILABLE","reason":str(exc)}
        checks.append(item)
    result = {
        "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source":"Binance public spot best bid/ask and sampled depth",
        "virtual_start_usdt":str(amount),"assumed_fee_per_leg":str(fee),
        "pairs":len(books),"triangles":len(ranked),"positive_indicative":len(positive),
        "depth_checked":checks,"verified_executable_profit":None,
        "notes":"Read-only; no synchronized executable orders. Regional permissions, full exchange filters and account fees not confirmed."
    }
    with open("results.json","w",encoding="utf-8") as f:
        json.dump(result,f,indent=2)
    print(json.dumps(result,indent=2))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("DATA_UNAVAILABLE:",exc,file=sys.stderr)
        sys.exit(2)
