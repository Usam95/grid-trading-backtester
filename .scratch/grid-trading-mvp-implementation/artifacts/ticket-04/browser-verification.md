# Ticket 04 Browser Verification

## Environment

- Server command: `.venv\Scripts\python.exe tools\run_studio_for_browser.py --port 8013`
- URL: `http://127.0.0.1:8013/studio/`
- Browser: Playwright Chromium
- Workflow: `tests/browser/migrated-backtest.spec.ts`

## Steps and observations

1. Opened the typed Research workspace and confirmed no online trading authority.
2. Observed the canonical adaptive-policy card with immutable operator inputs,
   admitted observation evidence, `RANGE_NORMAL`, mechanically derived plan, and
   explicit legacy semantic differences.
3. Recorded the visible deterministic identities:
   - Configuration: `sha256:b917ca037cfdce06d0796ec8e1009a8d618628aea6475e95f2b23c1b16517a15`
   - Observation: `sha256:3f0d688204bef0da2c4b986edd4685396bfbf089e6828016c5ae4d200da2094b`
   - Canonical event: `sha256:fe35e751cc794577b1d33b6f5129bad5c560cf1a4db1b43deca4c807365b788a`
   - Plan derivation causation: `sha256:fe35e751cc794577b1d33b6f5129bad5c560cf1a4db1b43deca4c807365b788a`
   - Grid plan epoch: `sha256:1a528bd9b55b5a367af924bb2068f2d1caf6d64481031a3bc056b8a94a31b2aa`
4. Executed the migrated backtest, navigated to its durable experiment URL, and
   reloaded the page.
5. Confirmed configuration, observation, event, derivation-causation, and
   epoch identities were unchanged after refresh.
6. Opened the Operations workspace and confirmed no command controls existed.
7. Navigated to `/` and confirmed the legacy Studio remained available.

## Result

- 2 browser tests passed.
- The visible adaptation state was `RANGE_NORMAL`; the legacy comparison showed
  120 bounded bars, effective ATR multiplier `2.0`, and 64 cancellation events.
- Refresh/navigation preserved deterministic identities.
- No screenshots were required or retained.
