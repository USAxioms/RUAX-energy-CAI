"""CAI-ENERGY-02 micro-grid sentinel: canonical WAD18 integer-only reference.
No floats. Stdlib only. Total on every well-formed 16-tuple of ints. Signed ops truncate toward zero.
ALL LIMITS BELOW ARE PLACEHOLDERS, NOT VERIFIED AGAINST ANY STANDARD OR UTILITY. Supply your own."""
import hashlib
from math import isqrt

WAD = 10**18
CAP = 10**24
V_NOM = WAD
F_NOM = 60 * WAD
V_MIN = 880000000000000000
V_MAX = 1100000000000000000
F_MIN = 59300000000000000000
F_MAX = 60500000000000000000
DROOP_R = 50000000000000000
Q_KV = 50000000000000000
P_MIN = -WAD
P_MAX = WAD
Q_MIN = -WAD
Q_MAX = WAD
DV_MAX = 50000000000000000
DF_MAX = 200000000000000000
DTH_MAX = 20 * WAD
P_TOL = 10000000000000000
THD_MAX = 50000000000000000
FULL_TURN = 360 * WAD
HALF_TURN = 180 * WAD
GAIN = 500000000000000000
REFINE_TOL = 1000000000000
MAX_ITER = 64
T_UV = 1
T_OV = 2
T_UF = 4
T_OF = 8
S_DV = 1
S_DF = 2
S_DTH = 4
S_BAL = 8
S_THD = 16
ACT_HOLD = 0
ACT_ISLAND = 1
ACT_RECONNECT = 2
ARITY = 16
GENESIS = bytes(32)
TRACE_KEYS = ("trip", "smask", "resid", "thd", "p_cmd", "q_cmd", "f_refined", "iters", "conv", "action")


def iabs(a):
    return a if a >= 0 else -a


def smul(a, b):
    q = (iabs(a) * iabs(b)) // WAD
    return -q if (a < 0) != (b < 0) else q


def sdiv(a, b):
    if b == 0:
        return 0
    q = (iabs(a) * WAD) // iabs(b)
    return -q if (a < 0) != (b < 0) else q


def clampv(x, lo, hi):
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x


def _digits(s):
    if s == "":
        return 0
    for c in s:
        if c not in "0123456789":
            return 0
    return 1


def parse_decimal(s):
    """Decimal string -> (ok, WAD int). >18 fractional digits truncate toward zero. No floats."""
    t = s.strip()
    neg = 0
    if t[:1] == "-":
        neg = 1
        t = t[1:]
    parts = t.split(".")
    if len(parts) > 2:
        return (0, 0)
    ip = parts[0]
    fp = parts[1] if len(parts) == 2 else ""
    if ip == "" and fp == "":
        return (0, 0)
    if ip != "" and _digits(ip) == 0:
        return (0, 0)
    if fp != "" and _digits(fp) == 0:
        return (0, 0)
    fp = (fp + "000000000000000000")[:18]
    v = (int(ip) if ip != "" else 0) * WAD + int(fp)
    v = clampv(v, 0, CAP)
    return (1, -v if neg == 1 else v)


def droop_p(f, p_set):
    dpu = sdiv(f - F_NOM, F_NOM)
    return clampv(p_set - sdiv(dpu, DROOP_R), P_MIN, P_MAX)


def droop_q(v, q_set):
    return clampv(q_set - sdiv(v - V_NOM, Q_KV), Q_MIN, Q_MAX)


def band_mask(v, f):
    m = 0
    if v < V_MIN:
        m += T_UV
    if v > V_MAX:
        m += T_OV
    if f < F_MIN:
        m += T_UF
    if f > F_MAX:
        m += T_OF
    return m


def norm_angle(a):
    r = a % FULL_TURN
    if r > HALF_TURN:
        r -= FULL_TURN
    return r


def thd(h1, h3, h5, h7):
    if h1 <= 0:
        return WAD
    s = 0
    for h in (h3, h5, h7):
        r = sdiv(iabs(h), h1)
        s += smul(r, r)
    return isqrt(s * WAD)


def sync_mask(f, v, dth, gf, gv, p_gen, p_load, p_batt, p_loss, thd_v):
    m = 0
    if iabs(v - gv) > DV_MAX:
        m += S_DV
    if iabs(f - gf) > DF_MAX:
        m += S_DF
    if iabs(norm_angle(dth)) > DTH_MAX:
        m += S_DTH
    resid = p_gen + p_batt - p_load - p_loss
    if iabs(resid) > P_TOL:
        m += S_BAL
    if thd_v > THD_MAX:
        m += S_THD
    return m, resid


def refine(f, f_ref, gain, tol, max_iter):
    """R3 recursive refinement: bounded deterministic contraction toward f_ref."""
    iters = 0
    for _ in range(max_iter):
        if iabs(f - f_ref) <= tol:
            break
        f = f - smul(gain, f - f_ref)
        iters += 1
    conv = 1 if iabs(f - f_ref) <= tol else 0
    return f, iters, conv


def clamp_inputs(tel):
    return tuple(clampv(x, -CAP, CAP) for x in tel)


def audit(tel):
    t = clamp_inputs(tel)
    f, v, gf, gv, dth = t[1], t[2], t[3], t[4], t[5]
    p_set, q_set, p_gen, p_load, p_batt, p_loss = t[6], t[7], t[8], t[9], t[10], t[11]
    h1, h3, h5, h7 = t[12], t[13], t[14], t[15]
    trip = band_mask(gv, gf)
    thd_v = thd(h1, h3, h5, h7)
    smask, resid = sync_mask(f, v, dth, gf, gv, p_gen, p_load, p_batt, p_loss, thd_v)
    if t[0] == 0:
        action = ACT_ISLAND if trip != 0 else ACT_HOLD
    else:
        action = ACT_RECONNECT if (trip == 0 and smask == 0) else ACT_HOLD
    fr, iters, conv = refine(f, F_NOM, GAIN, REFINE_TOL, MAX_ITER)
    return {"trip": trip, "smask": smask, "resid": resid, "thd": thd_v,
            "p_cmd": droop_p(f, p_set), "q_cmd": droop_q(v, q_set),
            "f_refined": fr, "iters": iters, "conv": conv, "action": action}


def _w(v):
    return (v % (2**256)).to_bytes(32, "big")


def next_hash(prev, n, tel, trace):
    data = prev + _w(n)
    for x in clamp_inputs(tel):
        data += _w(x)
    for k in TRACE_KEYS:
        data += _w(trace[k])
    return hashlib.sha256(data).digest()


def run(seq):
    """Audit chain over a telemetry sequence (a log fold, not a controller)."""
    h = GENESIS
    out = []
    for n, tel in enumerate(seq):
        tr = audit(tel)
        h = next_hash(h, n, tel, tr)
        out.append((tr, h.hex()))
    return out
