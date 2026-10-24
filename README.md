# MPTM Arbitrage Research

Read-only experimental triangular-arbitrage scanner. No orders, wallet, credentials, or real money.

Run `python scanner.py` to query Binance public market data and write `results.json`.

GitHub Actions runs on a 15-minute schedule (best effort), and can be triggered manually. Download the workflow artifact to review each run. This is NOT a continuous 48-hour backtest or proof of executable profits.

**Limitations:** Quotes are asynchronous and top-of-book only. No executable depth, order minimum, rounding, slippage, regional availability, or account-specific fees are validated. Never trade solely on these signals.
