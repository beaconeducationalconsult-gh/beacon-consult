# Deliveries — deferred work & infrastructure options

Status as of **2026-07-17**. Phase 0 (the delivery ledger, approval workflow,
and soft gate) is built and live for **lesson plans** and **schemes of
learning**. Phases 1 and 2 are **deferred by decision** — see below.

## Decision on record

We are **staying on the free tier and hardening later.** The current soft gate
(owner approves every delivery; agents only get watermarked "SAMPLE" previews)
plus **manual "Mark as paid"** is enough to launch and collect Mobile Money
payments at ₵0 infrastructure cost. Phases 1 and 2 both require server code,
which the free tier blocks (see options), so they wait until transaction volume
justifies moving to paid infrastructure.

**Revisit trigger:** when agents are consistently making sales and the manual
approve/mark-paid loop becomes a bottleneck, or when a savvy agent bypassing the
client-side soft gate becomes a real risk.

---

## Phase 1 — Hard gate (server-side generation)

**Goal:** make "I approve every download" airtight. Today the finished file is
generated in the browser, so the gate is *soft* — a determined agent could
generate a clean copy without approval. Phase 1 moves final generation
server-side so the clean file **cannot exist until the owner approves**.

**Design:** a server endpoint that (1) verifies the delivery doc is `approved`
in Firestore, (2) runs the existing generation logic (`lib/lessonPlanDocx.js`,
`lib/schemeDocx.js`, etc. — they run in Node), (3) streams the clean file back
(or stores it and returns a link). No watermark on the server output. The
client-side libs stay only for agent previews.

**Note:** generating from a *stored document* is why only lesson plans and
schemes are wired — the server can re-render them. Ad-hoc quizzes/question
papers would need to be persisted first (see below).

## Phase 2 — MoMo automation

**Goal:** auto-confirm payment so `paid` (and commission realization) happens
without the owner clicking "Mark paid."

**Design:** register a webhook with a Mobile Money gateway (Paystack, Hubtel, or
Flutterwave — all support Ghana MoMo, all charge per-transaction only, ~1.95%,
**no fixed monthly fee**). On payment, the gateway calls our webhook → verify
signature → set the delivery to `paid` in Firestore via the Admin SDK.

**Fallback already in place:** manual "Mark as paid" in the Approvals page lets
the owner collect MoMo and confirm by hand today, with zero integration. The
MoMo gateway is prudent to adopt whenever; only the *webhook automation* needs
the server infra below.

---

## Infrastructure options (the blocker)

Firebase's free **Spark** plan does **not** allow Cloud Functions — they require
the paid **Blaze** plan. So both phases need one of:

| Path | Enables | Cost | Trade-off |
|---|---|---|---|
| **Stay free** (chosen) | Soft gate + manual mark-paid only | ₵0 | Owner approves every download; agent previews watermarked. Sufficient to launch. |
| **Firebase Blaze** | Cloud Functions for Phase 1 + 2 | Free allowance ≈ ₵0 in practice; **card required**, no hard spend cap | Cleanest fit (already all-Firebase); small runaway-cost risk — set budget alerts |
| **Vercel functions** | Generate + stream clean file; MoMo webhook | Free to test on Hobby; **commercial use needs Vercel Pro (~$20/mo)** | Avoids Firebase Functions; needs Firebase Admin SDK + service-account setup; Hobby ToS is non-commercial |

**When we go paid:** Firebase Blaze is likely the cleaner target (server needs
Firestore Admin access + the doc libs anyway, and its free allowance should keep
real cost near ₵0). Vercel Pro is a predictable flat fee if runaway-cost risk is
the bigger worry.

---

## Also deferred (separate decisions, 2026-07-17)

- **Quizzes & question papers:** generated ad-hoc from a question selection with
  no stored doc. To deliver them, first **persist the generated artifact** as a
  Firestore doc (so it has a `materialRef` and Phase 1 can regenerate it). Then
  wire the same request→approve flow. Add watermark support to `lib/quizPptx.js`
  and `lib/questionPaper.js`.
- **Study notes:** no file export exists (network-only content). Would need a
  Word/PDF export lib built first before delivery could apply.

## Phase 3 (unchanged, further out)

School accounts (browse catalog, request purchases) and auto-approval trust
tiers for proven agents (so the owner isn't the rate limiter on revenue).
