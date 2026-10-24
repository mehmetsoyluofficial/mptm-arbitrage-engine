"""Read-only Binance triangular-arbitrage research. No trades or secrets."""
import datetime
import json
import sys
import urllib.request
from decimal import Decimal

BASE_URL = "https://data-api.binance.vision/api/v3/"

def fetch(endpoint):
    request = urllib.request.Request(
        BASE_URL + endpoint, headers={"User-Agent": "MPTM-research/0.4"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)

def triangles(books, symbols, start=Decimal("10"), fee=Decimal("0.001")):
    edges = {}
    for item in books:
        symbol = item["symbol"]
        if symbol not in symbols:
            continue
        base, quote = symbols[symbol]
        bid = Decimal(item["bidPrice"])
        ask = Decimal(item["askPrice"])
        if bid <= 0 or ask <= 0:
            continue
        edges[(base, quote)] = (bid * (1 - fee), symbol)
        edges[(quote, base)] = ((1 / ask) * (1 - fee), symbol)
    by_source = {}
    for (source, target), edge in edges.items():
        by_source.setdefault(source, []).append((target, edge))
    results = []
    for second, (rate1, sym1) in by_source.get("USDT", []):
        for third, (rate2, sym2) in by_source.get(second, []):
            if third in ("USDT", second):
                continue
            final_edge = edges.get((third, "USDT"))
            if not final_edge:
                continue
            rate3, sym3 = final_edge
            ending = start * rate1 * rate2 * rate3
            pct = (ending / start - 1) * 100
            results.append({
                "path": ["USDT", second, third, "USDT"],
                "pairs": [sym1, sym2, sym3],
                "estimated_end_usdt": str(round(ending, 8)),
                "estimated_pct": str(round(pct, 5)),
            })
    return sorted(results, key=lambda item: Decimal(item["estimated_pct"]), reverse=True)

def main():
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    info = fetch("exchangeInfo")
    symbols = {
        item["symbol"]: (item["baseAsset"], item["quoteAsset"])
        for item in info["symbols"]
        if item["status"] == "TRADING" and item.get("isSpotTradingAllowed", True)
    }
    books = fetch("ticker/bookTicker")
    candidates = triangles(books, symbols)
    output = {
        "timestamp_utc": timestamp,
        "source": "Binance public best bid/ask",
        "assumed_fee_per_leg": "0.1%",
        "starting_virtual_usdt": "10",
        "limitations": "Not executable: asynchronous prices; no depth, minimums, precision, slippage or region check",
        "pairs": len(books),
        "triangles": len(candidates),
        "positive_indicative": sum(Decimal(c["estimated_pct"]) > 0 for c in candidates),
        "top_10": candidates[:10],
    }
    with open("results.json", "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2)
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("DATA_UNAVAILABLE:", exc, file=sys.stderr)
        sys.exit(2)
