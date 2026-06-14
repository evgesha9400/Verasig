# Execution engine rules — exit semantics

Behavioral spec for how the exit engine reconciles the user's rules with signal-author updates. UI surfaces these in `ExecutionView.jsx` copy; the rules themselves are engine behavior.

## 1. The stop ratchet — "the tighter stop wins"

Both the user's rules (e.g. _move stop to break-even after TP1_) and the author's updates (when _Follow the author's updates_ is on) can move the stop. Resolution:

> **The stop only ever moves in the position's favor.** Whichever instruction yields the more protective stop at any moment wins. An author update can tighten the stop past the user's break-even; it can never loosen it back below.

Consequences:

- Author moves stop to BE _before_ TP1 → applied immediately (earlier than the user's rule — fine).
- Author trails the stop _above_ BE → applied (tighter).
- Author moves the stop _down_ ("giving it room") after the user's rule ratcheted to BE → **rejected**; stop stays at BE.

Rationale: the user's toggles are _guarantees_; the author's updates are _information_. No precedence setting is exposed — the rare user who wants "obey the author even when it loosens my stop" is not worth the config burden (revisit if real demand appears).

The UI states this only in the conflicting configuration: when both _Follow author_ and _Break-even after TP1_ are on, an info note appears under the switches.

## 2. Relative author updates resolve against YOUR position

Authors post relative instructions — _"move SL to break-even"_, _"close half"_ — without prices. The author doesn't know the follower's entry (the follower may have laddered, partially filled, or filled at a different price).

> Every relative update resolves against the **follower's actual position** at the moment it arrives. "Break-even" = the follower's average fill price. "Half" = half of the follower's current position.

## 3. Edge cases

### No fills yet

Author posts "move SL to BE" but none of the follower's entry orders filled → **no-op** (no position, no break-even). Optionally a signal-quality datapoint: the author is managing a trade the follower never entered.

### Partial ladder fills + stop ratchet (the sneaky one)

L1 and L2 filled, L3 hasn't; the stop ratchets to BE (avg of L1+L2). The L3 limit order now sits **below the stop**. If price drops: position stops out at BE, then L3 fills — silently reopening exposure with no stop logic attached.

> **Rule: when the stop ratchets to or above an unfilled entry level, cancel that entry order.** Declaring "no more downside on this trade" contradicts averaging in lower.

This is engine behavior the user should be able to trust without configuring. Keep it out of the config UI; document in tooltips/docs.

### Fallback anchoring

Fallback stop-loss and take-profit percentages (missing-risk handling, and "my own" mode) are anchored on the **average fill price**, recomputed as ladder levels fill.
