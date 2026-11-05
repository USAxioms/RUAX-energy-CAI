"""Deterministic vector generation: integer LCG + exact boundary sweeps. No floats."""
import json, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "ref"))
import energy as e
W = e.WAD
# (mode,f,v,gf,gv,dth,p_set,q_set,p_gen,p_load,p_batt,p_loss,h1,h3,h5,h7)
NOM = [0, 60 * W, W, 60 * W, W, 0, W // 2, 0, 6 * W // 10, W // 2, 0, W // 10, W, 3 * W // 100, 4 * W // 100, 0]
IDX = {"mode": 0, "f": 1, "v": 2, "gf": 3, "gv": 4, "dth": 5, "p_set": 6, "q_set": 7, "p_gen": 8,
       "p_load": 9, "p_batt": 10, "p_loss": 11, "h1": 12, "h3": 13, "h5": 14, "h7": 15}

def mk(**kw):
    t = list(NOM)
    for k, v in kw.items():
        t[IDX[k]] = v
    return tuple(t)

def sweeps():
    out = []
    for mode in (0, 1):
        for name, thr in (("gv", e.V_MIN), ("gv", e.V_MAX), ("gf", e.F_MIN), ("gf", e.F_MAX)):
            for d in (-1, 0, 1):
                out.append(mk(mode=mode, **{name: thr + d}))
    out += [mk(mode=1, v=W + e.DV_MAX + d) for d in (-1, 0, 1)]
    out += [mk(mode=1, v=W - e.DV_MAX + d) for d in (-1, 0, 1)]
    out += [mk(mode=1, f=60 * W + e.DF_MAX + d) for d in (-1, 0, 1)]
    out += [mk(mode=1, f=60 * W - e.DF_MAX + d) for d in (-1, 0, 1)]
    for base in (0, 360 * W, -360 * W, 720 * W):
        for d in (-1, 0, 1):
            out.append(mk(mode=1, dth=base + e.DTH_MAX + d))
            out.append(mk(mode=1, dth=base - e.DTH_MAX + d))
    out += [mk(mode=1, dth=x * W) for x in (180, -180, 181, -181, 179, 359, 360, 361, 540)]
    for d in (-1, 0, 1):
        out.append(mk(mode=1, p_gen=6 * W // 10 + e.P_TOL + d))
        out.append(mk(mode=1, p_gen=6 * W // 10 - e.P_TOL + d))
        out.append(mk(mode=1, p_batt=e.P_TOL + d))
        out.append(mk(mode=1, p_batt=-e.P_TOL + d))
        out.append(mk(mode=1, p_load=W // 2 + e.P_TOL + d))
        out.append(mk(mode=1, p_loss=W // 10 + e.P_TOL + d))
    out += [mk(mode=1, h3=5 * W // 100, h5=0), mk(mode=1, h3=5 * W // 100 + 10**12, h5=0),
            mk(mode=1, h3=-5 * W // 100, h5=0), mk(mode=1, h3=0, h5=0, h7=51 * W // 1000),
            mk(mode=1, h3=0, h5=0, h7=0), mk(mode=1, h1=0), mk(mode=1, h1=-W), mk(mode=1, h1=1),
            mk(mode=1, h1=2 * W, h3=W // 10, h5=W // 10, h7=-W // 20)]
    # droop clamps and exactness
    out += [mk(f=f) for f in (0, 30 * W, 59 * W, 60 * W + 1, 60 * W - 1, 61 * W, 120 * W, 300 * W)]
    out += [mk(f=60 * W + 36 * 10**15, p_set=-W), mk(f=60 * W - 36 * 10**15, p_set=W)]
    out += [mk(v=v) for v in (0, W // 2, W - 1, W + 1, 2 * W, 5 * W)]
    out += [mk(v=W + 5 * 10**16, q_set=-W), mk(v=W - 5 * 10**16, q_set=W), mk(q_set=-W), mk(q_set=W)]
    out += [mk(p_set=p) for p in (-2 * W, -W, W, 2 * W)]
    # refinement
    out += [mk(f=60 * W + x) for x in (e.REFINE_TOL - 1, e.REFINE_TOL, e.REFINE_TOL + 1, 1, -1, -e.REFINE_TOL)]
    out += [mk(f=x) for x in (59 * W, 61 * W, 10**23, 10**24, -10**24)]
    # clamp / negatives / caps
    out += [tuple([5] + [10**25] * 15), tuple([-1] + [-10**25] * 15), tuple([0] * 16),
            tuple([1] + [10**24] * 15), tuple([2] + [-10**24] * 15)]
    return out

def lcg(seed):
    x = seed
    while True:
        x = (x * 6364136223846793005 + 1442695040888963407) % (2**64)
        yield x >> 33

def generate(n=300):
    rows = [tuple(NOM)] + sweeps()
    g = lcg(20261104)
    for _ in range(n):
        r = [next(g) % 2, 55 * W + next(g) * 10**9 % (10 * W), 8 * W // 10 + next(g) * 10**9 % (4 * W // 10),
             58 * W + next(g) * 10**9 % (4 * W), 8 * W // 10 + next(g) * 10**9 % (4 * W // 10),
             next(g) * 10**10 % (800 * W) - 400 * W, next(g) * 10**6 % (2 * W) - W, next(g) * 10**6 % (2 * W) - W,
             next(g) * 10**6 % W, next(g) * 10**6 % W, next(g) * 10**6 % (2 * W) - W, next(g) * 10**6 % (W // 5),
             W // 2 + next(g) * 10**6 % W, next(g) * 10**6 % (W // 5) - W // 10,
             next(g) * 10**6 % (W // 5) - W // 10, next(g) * 10**6 % (W // 5) - W // 10]
        rows.append(tuple(r))
    return rows

if __name__ == "__main__":
    rows = generate()
    res = e.run(rows)
    out = [{"tel": list(r), "trace": t, "hash": h} for r, (t, h) in zip(rows, res)]
    with open(os.path.join(HERE, "vectors.json"), "w") as f:
        json.dump(out, f, sort_keys=True)
    print("vectors", len(out), "final", out[-1]["hash"])
