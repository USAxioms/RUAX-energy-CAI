# WAD18 Deterministic Micro-Grid Sentinel Logic: Reproducibility Capsule v0.1.0
2026-11-04 · off-chain, zero-dependency (Python stdlib: hashlib, math.isqrt)

## 1. Scope and honest limits
This capsule is a **pure, reproducible reference computation**: telemetry tuple in, decision trace out, plus a hash-chained audit log.
It is NOT a live controller, NOT a protection relay, and NOT safety-certified. Real trip functions belong in certified hardware (IEEE 1547 / UL 1741 class devices).
**Every threshold in ref/energy.py is a PLACEHOLDER**: not verified against IEEE 1547, a utility tariff, or any standard. Supply your own and regenerate the profile and vectors.
"R3 refinement" is implemented here as a bounded, fixed-gain contraction (§3.6); nothing here claims fidelity to any external framework by that name.

## 2. Axioms
A1 Exact integer arithmetic; value x is stored as x·10^18 (WAD). No floats: enforced by an AST lint (no float literals, no true division, no float(), no raise/assert, imports limited to hashlib and math).
A2 Total on every well-formed 16-tuple of integers: no exceptions; zero divisors return 0.
A3 Signed multiply/divide truncate toward zero; angle normalization uses Euclidean modulo (result in (-180°, 180°]).
A4 Inputs are clamped to ±10^24 (WAD), so EVM-width ports cannot overflow (largest product ≤10^48 ≪ 2^256).
A5 Sensor ingestion: ADC floats are not bit-exact. The boundary accepts integer counts or decimal strings via parse_decimal (truncates beyond 18 decimals toward zero; rejects malformed text with ok=0).

## 3. Model
Telemetry: mode (0 grid-tied, nonzero islanded), f, v, feeder f/v, phase difference, P/Q setpoints, generation, load, battery (+discharge), losses, harmonics h1,h3,h5,h7.
3.1 Droop. P = clamp(P_set − (Δf/f_nom)/R), Q = clamp(Q_set − (v−1)/K). Hand anchor: f=60.06 Hz, R=0.05, P_set=0.5 → P=0.48 exactly.
3.2 Islanding trip. Feeder (v,f) outside [V_MIN,V_MAX]×[F_MIN,F_MAX] sets bits UV=1, OV=2, UF=4, OF=8 (strict inequalities; bounds are inside the safe band). Grid-tied and any bit set → ISLAND.
3.3 THD = isqrt(Σ(h_k/h1)²·WAD); h1 ≤ 0 returns 100% (fail-safe). Hand anchor: h=(1, 0.03, 0.04, 0) → 0.05 exactly.
3.4 Reconnection (islanded): requires feeder healthy AND |Δv|≤DV, |Δf|≤DF, |normalized Δθ|≤DTH, |P_gen+P_batt−P_load−P_loss|≤P_TOL (power-balance residual; this is an accounting balance on supplied telemetry, not a thermodynamic proof), THD≤THD_MAX. Then RECONNECT, else HOLD.
3.5 Audit chain: h_{n+1}=SHA-256(h_n ‖ n ‖ clamped inputs ‖ trace fields), each a 32-byte two's-complement word; h_0=32 zero bytes. It is a log, not consensus; anchoring it on-chain is a separate step.
3.6 Refinement: repeat f ← f − gain·(f−f_ref) for at most MAX_ITER passes, stop when |f−f_ref|≤tol.

## 4. Theorems
T1 Totality: no unguarded division, bounded loops only, all operands integers. T2 Determinism: integer semantics + standardized SHA-256 ⇒ identical bytes on any conforming runtime.
T3 Range: P,Q ∈ [−1,1] WAD by clamps; trip<16, smask<32; action ∈ {0,1,2}.
T4 Refinement always converges under the default profile. With gain 0.5 and truncation, |e|←⌈|e|/2⌉, so e_k ≤ e_0/2^k + 1. Since |e_0| ≤ 2·10^24 (clamp), k=41 gives e_k < 10^12 = tol; 41 < 64 = MAX_ITER, so conv=1 and iters≤42 for every input.
T5 Boundary exactness: the vector suite sweeps each threshold at −1, 0, +1 ulp and the angle wraparounds, so a comparison-operator slip is observable.

## 5. Evidence executed in the build sandbox
- 437 golden vectors (boundary sweeps + integer-LCG cases); chain tail 11fb7121…cd54. Hand anchors pass.
- Mutation testing of ref/energy.py: every operator, and/or keyword, integer and string literal mutated once: 236 mutants, 224 non-equivalent, **224 killed (1000 permille)**; 12 proven equivalent (iabs at 0, sign test on zero operands, clamp at equality; proofs in tests/mutants.py).
- Constants are pinned by tests/profile.json, so changing a limit fails the suite until the profile and vectors are deliberately regenerated. That pin is a spec choice, and it is why constant mutants die.
- Ledger chain verifies; ZIP rebuilds byte-identically.

## 6. Not verified
Thresholds and standards compliance; real-time behavior (Python latency is not "instant"; this reference defines results, not timing); behavior on real telemetry; any on-chain anchoring; independent review.
