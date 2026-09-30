# Jacobian Conjecture — exact audit of the 2026 counterexamples

Independent, exact-arithmetic verification of the polynomial maps that refuted
the Jacobian conjecture in dimension three (July 2026). We verify pinned
published claims with two independent symbolic engines; **this is a
verification project, not a novelty claim.**

## The conjecture (Keller, 1939)

Let `F : C^n -> C^n` be a polynomial map whose Jacobian determinant
`det DF` is a nonzero constant. Then `F` is invertible with polynomial
inverse. The two-dimensional case is still open (Moh verified degree
<= 100); the conjecture held for degree <= 2 in every dimension (Wang).

## What happened in July 2026 (pinned sources)

| Date | Event | Source |
|---|---|---|
| 2026-07-19 | Alpoge announces a degree-7 counterexample in dimension 3 | cited as [11] in Gao, arXiv:2608.00222 |
| 2026-07-21 | Tao posts an annotated digestion with the explicit map | https://terrytao.wordpress.com/2026/07/21/a-digestion-of-the-jacobian-conjecture-counterexample/ |
| 2026-07-31 | Gao posts a self-contained account + new maps | https://arxiv.org/abs/2608.00222 (HTML v1: https://arxiv.org/html/2608.00222v1) |

Related but **not used for any claim in this repo**: arXiv:2609.17795
("An elementary way to find a counterexample"), Wikipedia's Jacobian
conjecture page, ulam.ai/research/jacobian.pdf.

## Claims we pin and verify

**Map F (Alpoge's counterexample)** — expanded components (identical in
Tao's eq. (1) and Gao's Section 3.4; variables `(x, y, z)`):

```
F1 = (1 + x*y)^3 * z + y^2 * (1 + x*y) * (4 + 3*x*y)
F2 = y + 3*x*(1 + x*y)^2 * z + 3*x*y^2 * (4 + 3*x*y)
F3 = 2*x - 3*x^2*y - x^3*z
```

1. `det J(F) == -2` identically (Gao, Theorem 3.3).
2. Component degrees are `(7, 6, 4)` (Gao, Theorem 3.3).
3. Three **distinct** rational points share one image
   (Gao, Section 3.4; Tao, same values):
   `F(0,0,-1/4) = F(1,-3/2,13/2) = F(-1,3/2,13/2) = (-1/4, 0, 0)`.
4. Structural identities tying the expanded components to the tangent-sweep
   data of Gao Section 3.4 (`p(w) = -3w^2+4w`, `q(w) = -w^3+w^2`,
   `gamma = 2 - 3xy - x^2 z`, `u = 1 + xy`, `w = gamma*u`):
   `F2*F3 == p(w) + 2*gamma`, `F1*F3^2 == q(w) + gamma*w`,
   `F3 == gamma*x`, plus the paper's factorizations
   `p(w)+2*gamma == gamma*BR2` and `q(w)+gamma*w == gamma^2*BR3`.

**Map G (Gao's degree-four example)** — Gao, Theorem 3.5:

5. `det J(G) == 2` identically.
6. Component degrees are `(4, 11, 12)`.
7. First component matches the printed expansion
   `g1 = -x^3 z - 4 x^2 y + 2 x`; the other two are reconstructed from
   the paper's closed-form sweep data and reproduced a second way by
   direct rational-function cancellation (SymPy route 2).

## Method (anti-circularity)

Three independent lines of evidence must agree before any claim is marked
VERIFIED:

- **Engine O** — a self-contained polynomial algebra + expression parser
  written for this repo (`fractions.Fraction` coefficients, no SymPy
  dependency at all), including Leibniz determinants over its own
  polynomial multiplication.
- **Engine S** — SymPy 1.14.0 symbolic polynomials, separate parser,
  separate kernel.
- **Structure** — the expanded components are checked against sweep
  identities whose data (`p`, `q`, `gamma`, `u`, `w`, brackets `BR2/BR3`)
  was transcribed from a *different passage* of the source than the
  components themselves. A single transcription typo in either place breaks
  an identity.

Both engines' polynomials are then compared term by term (components and
determinants). The self-test runs before every verification and pins
hand-computed fixtures; a self-test failure exits 2 and refuses to run.

## Results (2026-10-01, Python 3.14.4, SymPy 1.14.0, single thread)

Command: `python jacobian_verify.py --map all` — **exit 0**, verdict
`ALL_PINNED_CLAIMS_VERIFIED`, 30/30 claims, 22/22 self-test checks, 1.94 s.

| Claim | Engine O | Engine S | Cross-engine |
|---|---|---|---|
| F: `det J == -2` | OK | OK | agree |
| F: degrees `(7,6,4)` | OK | OK | agree |
| F: 3 distinct points -> `(-1/4,0,0)` | OK | OK | — |
| F: 3 structural identities + 2 factorizations | OK (5) | OK (5) | — |
| G: `det J == +2` | OK | OK | agree |
| G: degrees `(4,11,12)` | OK | OK | agree |
| G: `g1` printed expansion | OK | OK | — |
| G: route-2 cancellation reproduces `g2,g3` | — | OK | — |

Artifact: `results/verification_report.json` (per-map, per-engine detail).

### Hand fixtures (arithmetic worked out by hand, pinned in the self-test)

- `F(0,0,-1/4)`: `F1 = 1^3*(-1/4) + 0 = -1/4`, `F2 = F3 = 0`.
- `F(1,-3/2,13/2)`: `F3 = 2 + 9/2 - 13/2 = 0`;
  `F2 = -3/2 + 3*1*(1/4)*(13/2) + 3*1*(9/4)*(-1/2) = -3/2 + 39/8 - 27/8 = 0`;
  `F1 = (-1/8)(13/2) + (9/4)(-1/2)(-1/2) = -13/16 + 9/16 = -1/4`.
- `F(-1,3/2,13/2)`: same arithmetic with signs flipped; all three
  components land on `(-1/4, 0, 0)`.

### Source discrepancy resolved

A secondary source (an auto-transcribed YouTube clip) stated the common
image as `(1/4, 0, 0)`. Both primary sources say `(-1/4, 0, 0)`, and exact
rational evaluation of all three points confirms `(-1/4, 0, 0)`. The clip's
transcript is wrong by a sign.

### Development note: the gate caught two tool bugs

During development the self-test rejected a broken build twice:
(1) a constant-rendering bug that printed `det = -21` for the constant
`-2` (a stray monomial placeholder), and (2) a `Fraction`-vs-string type
mismatch that reported the collision check false while the values were
correct. Both are now guarded by the regression checks `po_str_constant`
and `po_str_mixed`. Fail-closed behavior (exit 2, refuse to run) worked as
designed.

## What we do NOT verify (honest bounds)

- **Generic fiber counts** (F has exactly 3 preimages for a generic point,
  G exactly 4): this needs Gröbner-basis elimination from Gao's appendix;
  we verify only the explicit collision for F and never claim fiber counts.
- **Global statements** ("not proper, fails injectivity only through points
  escaping to infinity", étale-covering framing): not re-proved here.
- **Gallagher's infinite family** (2026-07-20), Speyer's geometric
  explanation (2026-07-23), and Gao's higher-dimensional maps (degrees
  5, 6, 10, 12 in dimensions 4–5): not verified in this repo.
- **The planar case `n = 2`** remains open (Moh: degree <= 100). No sweep
  is run here; a planar search, if ever started, gets its own repo.
- The verification says nothing about novelty: all pinned claims are
  published results by Alpoge, Gao, and co-authors.

## How to run

```
python jacobian_verify.py --selftest      # self-test only
python jacobian_verify.py --map all       # verify both maps (default out: results/verification_report.json)
python jacobian_verify.py --map alpoge    # Alpoge's F only
python jacobian_verify.py --map gao       # Gao's G only
```

Exit codes: `0` = every pinned claim verified in exact arithmetic;
`1` = a pinned claim did NOT verify (stop and report — most likely a
transcription error; treat as unverified until re-checked by hand);
`2` = self-test failure (tool untrusted, refuses to run).

Requirements: Python 3.10+ (run here: 3.14.4), SymPy (run here: 1.14.0).
Engine O has no third-party dependency.

## License

MIT — see `LICENSE`.
