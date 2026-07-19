# Grid-Trading Research — Sources & Summaries

Curated sources behind the research section of the analysis. Each entry: **link · summary ·
relevance to grid-backtest-core**. Sources were gathered via live web search (2026-06) and reflect
both vendor/educational material and quantitative-finance commentary. Vendor blogs are marked as such
(use with appropriate skepticism); methodology claims are cross-checked against academic references.

---

## A. Grid-trading fundamentals & strategy taxonomy

1. **Binance Academy — "What Is Grid Trading?"**
   https://www.binance.com/en/academy/articles/what-is-grid-trading
   *Summary:* Defines grid trading, arithmetic vs geometric spacing, and the "buy low / sell high in a
   range" mechanic; emphasises ranging markets and the danger of strong trends.
   *Relevance:* Confirms the engine's core model (`SimpleGridStrategy` arithmetic/geometric spacing,
   `GridSpacing` enum) matches the canonical definition.

2. **Babypips — "Grid Trading" (School of Pipsology)**
   https://www.babypips.com/learn/forex/grid-trading
   *Summary:* Classic forex grid education; with-the-trend vs against-the-trend grids, no-stop
   martingale danger, importance of grid spacing relative to volatility.
   *Relevance:* Motivates ATR-based spacing (`SpacingPolicy`, `policies/space.py`) and trend filters
   (`FilterPolicy`).

3. **Investopedia — "Average True Range (ATR)"**
   https://www.investopedia.com/terms/a/averagetrueradge.asp
   *Summary:* ATR as a volatility measure for position sizing and stop placement.
   *Relevance:* Underpins `indicators.add_atr` and ATR-driven range/spacing/SLTP in the dynamic grid.

---

## B. Grid-bot landscape (competitor / market context)

4. **Pionex — "Best Grid Trading Bot Platforms"** *(vendor)*
   https://www.pionex.com/blog/best-grid-trading-bot/
   *Summary:* Catalogues grid-bot variants in production: regular, Infinity, leveraged, reverse,
   spot-futures arbitrage, AI grid, TWAP, DCA, martingale. Pionex bots are free; no classic
   walk-forward backtesting.
   *Relevance:* Defines the feature frontier the engine is measured against (leveraged/futures, reverse,
   infinity, DCA, AI parameterisation) — most of which the core does not yet model.

5. **Altrady — "Best Grid Trading Bots — Full Comparison"** *(vendor/affiliate)*
   https://www.altrady.com/blog/crypto-bots/best-grid-trading-bots
   *Summary:* Side-by-side of 3Commas, Bitsgap, Pionex, KuCoin, etc.; notes backtesting availability and
   futures-grid (Pro) tiers.
   *Relevance:* Competitive baseline for a productised offering; backtesting is a paid differentiator on
   3Commas/Bitsgap.

6. **HedgeWithCrypto — "Best Crypto Trading Bots: 2025 Reviews"** *(vendor/affiliate)*
   https://www.hedgewithcrypto.com/best-crypto-trading-bots/
   *Summary:* Pricing/feature overview; subscription tiers ($15–$149/mo) for 3Commas/Bitsgap; native
   exchange bots free.
   *Relevance:* Anchors realistic price points and the "free native bot" competitive pressure for
   monetization.

7. **Wallet Reviewer — "Pionex vs 3Commas"** *(vendor/affiliate)*
   https://walletreviewer.com/pionex-vs-3commas-comparison/
   *Summary:* Contrasts all-in-one exchange-bot (Pionex) vs multi-exchange automation (3Commas) with
   demo/backtest modes.
   *Relevance:* Two go-to-market archetypes a grid-backtest product could position against.

> Note: items 4–7 are commercial/affiliate content. They are reliable for *what features exist in
> market*, less so for performance claims. Treat any profitability figures as marketing.

---

## C. Adaptive / robust grid techniques

8. **Marcos López de Prado — *Advances in Financial Machine Learning* (Wiley, 2018)**
   https://www.wiley.com/en-us/Advances+in+Financial+Machine+Learning-p-9781119482086
   *Summary:* Regime detection, meta-labelling, cross-validation for finance, and extensive treatment of
   backtest overfitting.
   *Relevance:* Blueprint for adding regime-aware grids and *honest* validation (walk-forward, purged
   CV) — the core's biggest research gaps.

9. **Search-synthesised: ATR dynamic grid + trend filter + stop-loss (practitioner consensus)**
   *Summary:* Spacing as a multiple of ATR (e.g., 0.5–1.0×ATR), pause grids when ADX>~25 or price far
   from a long MA, and impose equity-/ATR-based global stops. Realistic monthly returns cited at ~2–10%
   with >30% drawdown risk in trends; "20%+/month" implies high ruin risk.
   *Relevance:* Validates the design of `SpacingPolicy`, `FilterPolicy` (RSI/EMA/ADX), and `SLTPPolicy`;
   also sets realistic, non-hype profitability expectations for any report the engine produces.

10. **Search-synthesised: Grid + DCA + ML regime detection**
    *Summary:* Combine grid (range profit) with DCA (entry smoothing) and ML regime detection (HMM,
    k-means, XGBoost) to switch/scale parameters by regime; adaptive grid width, layer count, and
    capital allocation per regime.
    *Relevance:* Concrete roadmap for a differentiated "adaptive grid research" product on top of the
    existing sweep infrastructure (`GridResearchRunner`).

---

## D. Risk & backtesting methodology (the cautionary literature)

11. **David Bailey & Marcos López de Prado — "The Deflated Sharpe Ratio" (SSRN, 2014)**
    https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
    *Summary:* Sharpe ratios are inflated when many strategies/parameters are tried; the Deflated Sharpe
    Ratio corrects for selection bias, track-record length, and non-normality.
    *Relevance:* Directly applicable to `GridResearchRunner` sweeps — without deflation, the "best" grid
    is often noise. Recommend adding DSR to sweep ranking.

12. **Bailey, Borwein, López de Prado, Zhu — "Pseudo-Mathematics and Financial Charlatanism / The
    Probability of Backtest Overfitting" (2014/2016)**
    https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659
    *Summary:* Formalises how easy it is to produce a great in-sample backtest by chance; introduces PBO
    (Probability of Backtest Overfitting) and CSCV.
    *Relevance:* Core justification for walk-forward/OOS being *mandatory* before any grid result is
    presented as decision-grade.

13. **Intrabar fill optimism on OHLC data (methodology consensus)**
    *Summary:* Assuming a limit order fills whenever a bar's high/low touches its price overstates fills
    because OHLC hides intrabar sequence; remedies are tick data, conservative fills, or
    queue/partial-fill modelling.
    *Relevance:* Precisely the weakness in `engine._simulate_fills_for_candle` (same-bar fill, no
    intrabar ordering, no partials). Strong support for adding a conservative fill mode.

14. **Risk synthesis: martingale grids, leverage & liquidation, fat tails**
    *Summary:* Martingale-style sizing turns a high win-rate into eventual ruin; leveraged/futures grids
    add forced liquidation that naive backtests ignore; fat-tail events (Taleb) devastate range-bound
    strategies during trends/breakouts. Frequently-cited references: Chan, *Quantitative Trading*;
    Taleb, *The Black Swan*; Kelly-criterion vs martingale growth analysis.
    *Relevance:* Explains why the engine's missing leverage/liquidation modelling is not cosmetic — it
    is the difference between an honest and a dangerously optimistic leveraged-grid report.

---

## E. How these sources shaped the analysis

- **Strategy taxonomy (A, B)** → the gap table's coverage of arithmetic/geometric/neutral/short/futures
  grids and DCA/martingale variants.
- **Adaptive techniques (C)** → confirmed the dynamic-grid policy design is on the right track and
  pointed to regime-detection as the differentiator.
- **Methodology/risk (D)** → drove the highest-priority recommendations: conservative intrabar fills,
  walk-forward + Monte Carlo + deflated Sharpe, and honest leverage/liquidation modelling.

*Caveat:* Several summaries (items 9, 10, 13, 14) are syntheses of multiple search results rather than a
single canonical URL; the named books/papers (8, 11, 12) and educational/vendor pages (1–7) are
directly linkable. Profitability figures from vendor material are marketing, not evidence.
