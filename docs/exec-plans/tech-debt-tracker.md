<!-- last_verified: 2026-07-08 -->
# Tech Debt Tracker

Known tech debt items. Agents update this when they discover or create tech debt.

| Description | Impact | Proposed Resolution | Priority | Status |
|---|---|---|---|---|
| _(none yet)_ | | | | |

## 2026-07-08 — verify

Nitpicks from the `/sample-3-verify` UX funnel (verdict PASS — marquee background-removal
works end-to-end). The first three were flagged as friction by a detection lens but the
adversarial screenshot gate ruled them OVER-CLAIMED and demoted them to nitpicks; none block
the goal. Screenshots live under `.local/verify/<lens>/` (gitignored evidence).

- /products/new form + /products/[sku] detail — "Remove background now" toggle is OFF by default, so the default create-submit lands the product in "Pending" with no cutout and the goal needs a separate "Remove background" click → auto-run-on-create is opt-in; consider defaulting it ON (or nudging it) for the "remove the background" first-time intent (shot .local/verify/A/02-new-product-form.png, .local/verify/A/04-detail-pending.png) [gate: OVER-CLAIMED, demoted from friction]
- product detail + catalog, during removal — the in-progress affordance is a motion-free disabled text label ("Removing…" / "Processing…") with a static icon; no animated spinner and no progress bar → on multi-second CPU / alpha-matting / large-image runs it can read as frozen; add a spinner/heartbeat (shot .local/verify/B/04-single-removing-midrun.png, .local/verify/B/13-batch-processing-real.png) [gate: OVER-CLAIMED + NEEDS-SOURCE-CHECK, demoted from friction]
- product detail CUTOUT pane at completion — the pane shows a blank transparency checkerboard for ~1s after the "Cutout ready" badge + toast fire while the PNG loads from B2 (no per-image skeleton) → success feedback precedes the painted image; add a per-image loading skeleton (shot .local/verify/B/05-single-done.png) [gate: OVER-CLAIMED, demoted from friction]
- /products/new "Safe test run" guidance — the FormDescription lists which fields to keep at defaults but omits the "Remove background now" toggle → mention enabling it for a one-submit result (shot .local/verify/A/02-new-product-form.png)
- catalog "Process all pending" — the batch button shows an indeterminate "Processing…" with no done/remaining count or progress bar → no sense of progress for a large pending queue (shot .local/verify/B/13-batch-processing-real.png)
- product detail (dev mode only) — the Next.js dev overlay shows "1 Issue": a React hydration mismatch warning ("A tree hydrated but some attributes of the server rendered HTML didn't match the client properties") → dev-only, does not affect the flow, but worth resolving before publish (shot .local/verify/C/04-detail-done-default.png)
