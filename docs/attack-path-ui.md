# Attack-Path Visualization (Member 4, Wave B / Phase 6 frontend)

Turns Member 3's node/link JSON (Contract 2, `GET /scans/{id}/attack-paths`) into an
interactive graph. Built and scaffolded before Member 3's backend exists, against a
mock published in `frontend/src/mocks/data.ts` (`attackPathsById`) that matches the
contract exactly — swapping to the real endpoint is MSW no longer intercepting the
route, not a rewrite.

## Status

Not yet integrated into a shared scan-detail tab nav — Member 2 hasn't built one yet.
Reachable directly at `/scans/:id/attack-paths` in the meantime (routed in `App.tsx`
the same way Dashboard was originally added). Not yet wired to a real backend — Member
3's endpoint, and the collector extension it depends on (EC2 instances, IAM role
attachments), don't exist yet either.

## Files

```
frontend/src/features/attack_paths/
├── AttackPathPage.tsx      data fetching, loading/error/empty states, path selection
├── AttackPathGraph.tsx     the force graph + the accessible node-button list
├── AttackPathLegend.tsx    severity + relationship keys
└── AttackPathDetails.tsx   selected-node panel, click-through to the related finding
```

## Graph visualization

`react-force-graph-2d` renders `nodes`/`links` from Contract 2 directly — the API's
`id`/`source`/`target` fields already match what the library expects, no reshaping
needed. Node color and the severity legend both come from the same
`SEVERITY_COLORS` map already used by `Badge`/`SeverityBadge` and the Dashboard's
charts (`Low`→gray, `Medium`→yellow, `High`→orange, `Critical`→red), so the graph
reads as the same visual language as the rest of the app rather than inventing a new
palette.

## Interaction model

- **Hover** a node or link for a tooltip (`label · type · risk N` for nodes, the
  relationship name for links).
- **Click** a node — on the canvas, or in the always-visible button list beneath it
  (see Accessibility) — to open its details panel.
- **Select a path** via the path buttons above the graph, sorted most-severe-first
  (same `Critical > High > Medium > Low` ordering `FindingsTable`/`DashboardPage`
  already use). Selecting a path dims every node and link *not* on it rather than
  hiding them, so the path reads clearly without losing the graph's overall shape.
  "All" (the default) clears the selection.

## Severity and risk styling

Node fill color is severity, matching the rest of the app. `risk_score` (from Wave
A's ML scoring, threaded through Contract 2 as an optional field) surfaces in the
hover tooltip and in the details panel when present — it's additive information, not
a second color channel, so it never competes with the severity encoding.

## Path highlighting

Implemented via a `Set` of the selected path's node ids: any node/link not in that
set renders in a flat gray (`#d1d5db`) instead of its normal color. This is
recomputed per render from the `AttackPathEntry.nodes` array Contract 2 already
provides — no separate highlighting API needed.

## Finding navigation (click-through)

Contract 2 puts `finding_id` on each node. **That field doesn't have a stable backing
value yet** — `FindingResponse` (the existing findings API) has no `finding_id` field
today, only `resource_id`/`rule_id`/etc. The mock (and this UI) uses the finding's
`resource_id` as a stand-in, since that's the only identifier the app currently
exposes. The details panel's "View related finding" link goes to `/scans/{scanId}`
(today's findings view) rather than a specific finding row, since there's no
finding-level route yet either. **Before Member 3 ships the real endpoint**, this
needs a decision: either `finding_id` stays `resource_id` for good, or a real
`finding_id` gets added to `FindingResponse` — whichever it is, this UI already
matches on it consistently, so it's a one-line change either way, not a rework.

## Accessibility

The canvas has no native focus or selection model — a mouse is the only way to pick
a node in the force layout itself. `AttackPathGraph` also renders a plain button per
node directly beneath the canvas (`role="group" aria-label="Select a resource"`),
always visible rather than hidden until focus, so keyboard and screen-reader users
have a real second path to the same interaction, and anyone who'd rather read a list
than parse a force layout can just do that instead.

## States

Loading (`Spinner`), API error, scan-not-found (404, worded the same way
`ScanDetailPage` already does), and a genuinely empty graph — worded as "no attack
paths found for this scan," a valid result per the Wave B plan's own guardrail, not
an error state dressed up to look like one.

## Tests

`AttackPathPage.test.tsx` covers: rendering with real mock data, path sort order,
the highlight/reset toggle (via `aria-pressed`, not canvas pixel-reading), the
accessible node list independent of the canvas, node-details click-through (with and
without a `finding_id`), the empty-graph state, and the 404 state.
`react-force-graph-2d` is mocked to a stub in tests — jsdom has no
`CanvasRenderingContext2D`, so anything canvas-drawn is untestable in this
environment by construction; the accessible node list exists in the real component
regardless of the mock, so it's what the click-through tests actually exercise.
