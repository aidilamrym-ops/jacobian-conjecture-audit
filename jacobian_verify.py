#!/usr/bin/env python3
"""Exact verification of the 2026 counterexamples to the Jacobian conjecture.

Pinned claims (primary sources in SOURCES below):

  [F] Alpoge's counterexample, announced 2026-07-19 (restated by Tao
      2026-07-21 and by Gao, arXiv:2608.00222, Section 3.4 / Theorem 3.3):
        * component degrees (7, 6, 4)
        * det J(F) == -2 identically
        * F(0,0,-1/4) = F(1,-3/2,13/2) = F(-1,3/2,13/2) = (-1/4,0,0)
          (three distinct points with one common image)

  [G] Gao's three-dimensional example of geometric degree four
      (arXiv:2608.00222, Theorem 3.5):
        * component degrees (4, 11, 12)
        * det J(G) == 2 identically
        * first component g1 = -x^3 z - 4 x^2 y + 2 x (as printed in the
          paper's expanded listing)

Method (anti-circularity -- independent lines that must agree):
  Engine O   a self-contained polynomial algebra + expression parser written
             for this file; coefficients are fractions.Fraction; this engine
             never imports SymPy.
  Engine S   SymPy symbolic algebra (separate parser, separate kernel).
  Structure  both engines check the sweep factorization identities from Gao
             Sections 3.4/3.5 (p(w), q(w), gamma, u, w, and the bracket
             factors are transcribed from a DIFFERENT passage than the
             expanded components), and the two engines' resulting polynomials
             are then compared term by term.

Exit codes:
  0  every pinned claim verified in exact arithmetic
  1  a pinned claim did NOT verify -- stop and report (most likely a
     transcription error; do not interpret as a mathematical result)
  2  self-test failure: the tool itself is untrusted
"""

import argparse
import json
import os
import re
import sys
import time
from fractions import Fraction as Q

__version__ = "1.0.0"

SOURCES = {
    "tao_blog": "https://terrytao.wordpress.com/2026/07/21/a-digestion-of-the-jacobian-conjecture-counterexample/",
    "gao_arxiv": "https://arxiv.org/abs/2608.00222",
    "gao_html": "https://arxiv.org/html/2608.00222v1",
}

VARS = ("x", "y", "z")

# ---------------------------------------------------------------------------
# Transcribed source data.  Every item below was cross-checked against two
# independent publications (Tao's blog post and Gao's arXiv paper agree
# verbatim on the expanded components of F and on the three colliding points).
# ---------------------------------------------------------------------------

# Alpoge's map F, expanded form (Gao, Sec. 3.4; Tao, eq. (1)).
F_COMPONENTS = [
    "(1 + x*y)**3*z + y**2*(1 + x*y)*(4 + 3*x*y)",
    "y + 3*x*(1 + x*y)**2*z + 3*x*y**2*(4 + 3*x*y)",
    "2*x - 3*x**2*y - x**3*z",
]
F_POINTS = [
    (Q(0), Q(0), Q(-1, 4)),
    (Q(1), Q(-3, 2), Q(13, 2)),
    (Q(-1), Q(3, 2), Q(13, 2)),
]
F_IMAGE = (Q(-1, 4), Q(0), Q(0))
F_DEGREES = (7, 6, 4)
F_DET = Q(-2)

# Gao's map G, first component as printed (Sec. 3.5); the other two are
# reconstructed from the paper's own closed-form sweep data and then
# cross-checked against the printed degree/claim data.
G1_PRINTED = "-x**3*z - 4*x**2*y + 2*x"
G_DEGREES = (4, 11, 12)
G_DET = Q(2)

# gamma = gamma0 + a*xy + b*x^2 z   as exponent-term tables {(i,j,k): coeff}
GAMMA_F = {(0, 0, 0): Q(2), (1, 1, 0): Q(-3), (2, 0, 1): Q(-1)}
GAMMA_G = {(0, 0, 0): Q(2), (1, 1, 0): Q(-4), (2, 0, 1): Q(-1)}
U_TERMS = {(0, 0, 0): Q(1), (1, 1, 0): Q(1)}  # u = 1 + x*y

# p(w), q(w) as coefficient tuples indexed by the power of w.
P_F = (Q(0), Q(4), Q(-3), Q(0))             # p(w) = -3 w^2 + 4 w
QQ_F = (Q(0), Q(0), Q(1), Q(-1))            # q(w) = -w^3 + w^2
P_G = (Q(0), Q(6), Q(-6), Q(1))             # p(w) = w^3 - 6 w^2 + 6 w
QQ_G = (Q(0), Q(0), Q(3, 2), Q(-2), Q(3, 8))  # q(w) = 3/8 w^4 - 2 w^3 + 3/2 w^2

# Factorization brackets from Gao:  p(w)+2*gamma = gamma * BR2,
#                                   q(w)+gamma*w = gamma^2 * BR3.
# Entries: (coefficient, power_of_gamma, power_of_u).
BR_F2 = [(Q(-3), 1, 2), (Q(4), 0, 1), (Q(2), 0, 0)]
BR_F3 = [(Q(-1), 1, 3), (Q(1), 0, 2), (Q(1), 0, 1)]
BR_G2 = [(Q(6), 0, 1), (Q(-6), 1, 2), (Q(1), 2, 3), (Q(2), 0, 0)]
BR_G3 = [(Q(3, 8), 2, 4), (Q(-2), 1, 3), (Q(3, 2), 0, 2), (Q(1), 0, 1)]

MAPS = {
    "alpoge": {
        "id": "alpoge_F",
        "components": F_COMPONENTS,
        "det": F_DET,
        "degrees": F_DEGREES,
        "gamma": GAMMA_F,
        "p": P_F,
        "q": QQ_F,
        "br2": BR_F2,
        "br3": BR_F3,
        "points": F_POINTS,
        "image": F_IMAGE,
        "g1_printed": None,
    },
    "gao": {
        "id": "gao_G",
        "components": None,
        "det": G_DET,
        "degrees": G_DEGREES,
        "gamma": GAMMA_G,
        "p": P_G,
        "q": QQ_G,
        "br2": BR_G2,
        "br3": BR_G3,
        "points": None,
        "image": None,
        "g1_printed": G1_PRINTED,
    },
}

# ===========================================================================
# Engine O -- own polynomial algebra over fractions.Fraction.
# A polynomial is a dict {(i, j, k): Fraction} in variables (x, y, z).
# ===========================================================================

ZERO_P = {}


def po_const(c):
    c = Q(c)
    return {} if c == 0 else {(0, 0, 0): c}


def po_var(idx):
    e = [0, 0, 0]
    e[idx] = 1
    return {tuple(e): Q(1)}


def po_prune(d):
    return {k: v for k, v in d.items() if v != 0}


def po_add(a, b):
    r = dict(a)
    for k, v in b.items():
        r[k] = r.get(k, Q(0)) + v
    return po_prune(r)


def po_neg(a):
    return {k: -v for k, v in a.items()}


def po_sub(a, b):
    return po_add(a, po_neg(b))


def po_mul(a, b):
    r = {}
    for (i1, j1, k1), c1 in a.items():
        for (i2, j2, k2), c2 in b.items():
            e = (i1 + i2, j1 + j2, k1 + k2)
            r[e] = r.get(e, Q(0)) + c1 * c2
    return po_prune(r)


def po_pow(a, n):
    r = po_const(1)
    for _ in range(n):
        r = po_mul(r, a)
    return r


def po_scale(a, c):
    c = Q(c)
    if c == 0:
        return {}
    return {k: v * c for k, v in a.items()}


def po_deriv(a, idx):
    r = {}
    for e, c in a.items():
        n = e[idx]
        if n:
            e2 = list(e)
            e2[idx] = n - 1
            r[tuple(e2)] = c * n
    return po_prune(r)


def po_deg(a):
    """Total degree (max i+j+k); the empty polynomial is degree -1."""
    if not a:
        return -1
    return max(i + j + k for (i, j, k) in a)


def po_eval(a, pt):
    s = Q(0)
    px, py, pz = pt
    for (i, j, k), c in a.items():
        s += c * px ** i * py ** j * pz ** k
    return s


def po_str(a):
    if not a:
        return "0"
    parts = []
    for e in sorted(a, reverse=True):
        c = a[e]
        i, j, k = e
        mono = ""
        for name, pw in (("x", i), ("y", j), ("z", k)):
            if pw == 1:
                mono += name
            elif pw > 1:
                mono += "%s^%d" % (name, pw)
        num, den = c.numerator, c.denominator
        if not mono:
            # Pure constant term: print the number itself.  Never append a
            # monomial placeholder "1" here (that rendered -2 as "-21").
            parts.append(str(num) if den == 1 else "%d/%d" % (num, den))
            continue
        coeff = str(num) if den == 1 else "%d/%d" % (num, den)
        if coeff == "1":
            coeff = ""
        elif coeff == "-1":
            coeff = "-"
        parts.append("%s%s" % (coeff, mono))
    return " + ".join(parts).replace("+ -", "- ")


_PERMS3 = (
    ((0, 1, 2), 1), ((0, 2, 1), -1), ((1, 0, 2), -1),
    ((1, 2, 0), 1), ((2, 0, 1), 1), ((2, 1, 0), -1),
)


def po_det3(m):
    """Leibniz determinant of a 3x3 matrix of polynomials."""
    acc = {}
    for perm, sgn in _PERMS3:
        t = po_const(sgn)
        for i in range(3):
            t = po_mul(t, m[i][perm[i]])
        acc = po_add(acc, t)
    return acc


def po_div_xn(a, n):
    """Exact division by x**n; raises if any term lacks the factor."""
    r = {}
    for (i, j, k), c in a.items():
        if i < n:
            raise ValueError("polynomial not divisible by x^%d" % n)
        r[(i - n, j, k)] = c
    return r


# ---------------------------------------------------------------------------
# Tiny expression parser for Engine O (supports + - * / ** () and integers).
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"\s*(?:(\d+)|([A-Za-z_][A-Za-z_0-9]*)|(\*\*)|([+\-*/()]))")


def _tokenize(src):
    toks, pos = [], 0
    s = src.strip()
    while pos < len(s):
        m = _TOKEN_RE.match(s, pos)
        if not m:
            raise ValueError("bad token at %d in %r" % (pos, src))
        pos = m.end()
        if m.group(1) is not None:
            toks.append(("num", int(m.group(1))))
        elif m.group(2) is not None:
            toks.append(("name", m.group(2)))
        elif m.group(3) is not None:
            toks.append(("**", "**"))
        else:
            toks.append((m.group(4), m.group(4)))
    return toks


class _Parser(object):
    def __init__(self, toks):
        self.toks = toks
        self.i = 0

    def peek(self):
        return self.toks[self.i] if self.i < len(self.toks) else (None, None)

    def next(self):
        tok = self.peek()
        self.i += 1
        return tok

    def expect(self, val):
        tok = self.next()
        if tok[0] != val:
            raise ValueError("expected %r, got %r" % (val, tok))

    def parse(self):
        e = self.expr()
        if self.i != len(self.toks):
            raise ValueError("trailing tokens: %r" % (self.toks[self.i:],))
        return e

    def expr(self):
        lhs = self.term()
        while self.peek()[0] in ("+", "-"):
            op = self.next()[0]
            rhs = self.term()
            lhs = po_add(lhs, rhs) if op == "+" else po_sub(lhs, rhs)
        return lhs

    def term(self):
        lhs = self.unary()
        while self.peek()[0] in ("*", "/"):
            op = self.next()[0]
            rhs = self.unary()
            if op == "*":
                lhs = po_mul(lhs, rhs)
            else:
                if set(rhs) != {(0, 0, 0)}:
                    raise ValueError("Engine O only divides by constants")
                lhs = po_scale(lhs, Q(1) / rhs[(0, 0, 0)])
        return lhs

    def unary(self):
        if self.peek()[0] == "-":
            self.next()
            return po_neg(self.unary())
        if self.peek()[0] == "+":
            self.next()
            return self.unary()
        return self.power()

    def power(self):
        base = self.atom()
        if self.peek()[0] == "**":
            self.next()
            tok = self.next()
            if tok[0] != "num":
                raise ValueError("exponent must be a non-negative integer literal")
            return po_pow(base, tok[1])
        return base

    def atom(self):
        kind, val = self.next()
        if kind == "num":
            return po_const(val)
        if kind == "name":
            if val not in VARS:
                raise ValueError("unknown variable %r" % val)
            return po_var(VARS.index(val))
        if kind == "(":
            e = self.expr()
            self.expect(")")
            return e
        raise ValueError("unexpected token %r" % (val,))


def parse_expr(src):
    return _Parser(_tokenize(src)).parse()


# ---------------------------------------------------------------------------
# Structure builders (Engine O).
# ---------------------------------------------------------------------------

def _po_poly_in(w, coefs):
    r = {}
    for c in reversed(coefs):
        r = po_add(po_mul(r, w), po_const(c))
    return r


def o_structure(gamma_terms, p_coefs, q_coefs):
    gam = dict(gamma_terms)
    u = dict(U_TERMS)
    w = po_mul(gam, u)
    return gam, u, w, _po_poly_in(w, p_coefs), _po_poly_in(w, q_coefs)


def o_bracket(br_data, gam, u):
    r = {}
    for c, ag, au in br_data:
        r = po_add(r, po_scale(po_mul(po_pow(gam, ag), po_pow(u, au)), c))
    return r


# ===========================================================================
# Engine S -- SymPy.
# ===========================================================================

try:
    import sympy as sp

    X, Y, Z = sp.symbols("x y z")
    _SYMPY_OK = True
    _SYMPY_ERR = ""
except Exception as exc:  # pragma: no cover
    sp = None
    _SYMPY_OK = False
    _SYMPY_ERR = str(exc)


def S(q):
    return sp.Rational(q.numerator, q.denominator)


def s_parse(src):
    return sp.sympify(src, locals={"x": X, "y": Y, "z": Z})


def s_structure(gamma_terms, p_coefs, q_coefs):
    gam = sum(S(c) * X ** i * Y ** j * Z ** k
              for (i, j, k), c in gamma_terms.items())
    u = 1 + X * Y
    w = sp.expand(gam * u)

    def poly_in(coefs):
        r = 0
        for c in reversed(coefs):
            r = sp.expand(r * w + S(c))
        return r

    return gam, u, w, poly_in(p_coefs), poly_in(q_coefs)


def s_bracket(br_data, gam, u):
    return sp.expand(sum(S(c) * gam ** ag * u ** au
                         for c, ag, au in br_data))


def s_div_xn(expr, n):
    """Exact division by x**n; raises if not divisible."""
    poly = sp.Poly(expr, X, Y, Z)
    out = 0
    for (i, j, k), c in poly.terms():
        if i < n:
            raise ValueError("sympy: polynomial not divisible by x^%d" % n)
        out += sp.Rational(c) * X ** (i - n) * Y ** j * Z ** k
    return sp.expand(out)


def s_components_equal(a, b):
    return sp.expand(a - b) == 0


def po_to_sympy(a):
    out = 0
    for (i, j, k), c in a.items():
        out += S(c) * X ** i * Y ** j * Z ** k
    return sp.expand(out)


def s_to_po(expr):
    out = {}
    if sp.expand(expr) == 0:
        return out
    for (i, j, k), c in sp.Poly(expr, X, Y, Z).terms():
        out[(i, j, k)] = Q(int(c.p), int(c.q))
    return out


# ===========================================================================
# Checks
# ===========================================================================

def check_structure(mp, gam, u, w, pw, qw, engine):
    """Factorization claims from Gao (common to both maps/engines)."""
    br2 = (o_bracket(mp["br2"], gam, u) if engine == "own"
           else s_bracket(mp["br2"], gam, u))
    br3 = (o_bracket(mp["br3"], gam, u) if engine == "own"
           else s_bracket(mp["br3"], gam, u))
    if engine == "own":
        fac1 = po_add(pw, po_scale(gam, Q(2))) == po_mul(gam, br2)
        fac2 = po_add(qw, po_mul(gam, w)) == po_mul(po_pow(gam, 2), br3)
    else:
        fac1 = sp.expand(pw + 2 * gam - gam * br2) == 0
        fac2 = sp.expand(qw + gam * w - gam ** 2 * br3) == 0
    return br2, br3, bool(fac1), bool(fac2)


def run_own(mp):
    """Engine O checks for one map; returns (report_dict, components)."""
    r = {"engine": "own"}
    gam, u, w, pw, qw = o_structure(mp["gamma"], mp["p"], mp["q"])
    br2, br3, fac1, fac2 = check_structure(mp, gam, u, w, pw, qw, "own")
    r["factor_p_plus_2gamma"] = fac1
    r["factor_q_plus_gamw"] = fac2

    if mp["components"] is not None:
        comps = [parse_expr(s) for s in mp["components"]]
        f1, f2, f3 = comps
        # Structural identities tying the expanded components to the sweep data.
        r["identity_f2_f3"] = po_mul(f2, f3) == po_add(pw, po_scale(gam, Q(2)))
        r["identity_f1_f3sq"] = (
            po_mul(f1, po_pow(f3, 2)) == po_add(qw, po_mul(gam, w)))
        r["identity_f3_gam_x"] = f3 == po_mul(gam, po_var(0))
        # The three colliding points.
        images = [tuple(po_eval(c, pt) for c in comps) for pt in mp["points"]]
        r["images"] = [[str(v) for v in im] for im in images]
        image_str = [str(v) for v in mp["image"]]
        # NOTE: `images` holds Fraction tuples on this path (the sympy path
        # holds strings) -- stringify before comparing, or the check fails on
        # a type mismatch even when the values are correct.
        r["collision_ok"] = all(
            [str(v) for v in im] == image_str for im in images)
        r["points_distinct"] = len(set(mp["points"])) == len(mp["points"])
    else:
        # Reconstruct G from the paper's closed-form sweep data:
        # g1 = gamma*x, g2 = BR2/x, g3 = BR3/x^2.
        x_var = po_var(0)
        g1 = po_mul(gam, x_var)
        g2 = po_div_xn(br2, 1)
        g3 = po_div_xn(br3, 2)
        comps = [g1, g2, g3]
        printed = parse_expr(mp["g1_printed"])
        r["g1_matches_printed"] = (g1 == printed)

    jac = [[po_deriv(comps[i], j) for j in range(3)] for i in range(3)]
    det = po_det3(jac)
    r["det"] = po_str(det)
    r["det_ok"] = (det == po_const(mp["det"]))
    r["degrees"] = [po_deg(c) for c in comps]
    r["degrees_ok"] = tuple(r["degrees"]) == tuple(mp["degrees"])
    return r, comps


def run_sympy(mp):
    """Engine S checks for one map; returns (report_dict, components)."""
    r = {"engine": "sympy"}
    gam, u, w, pw, qw = s_structure(mp["gamma"], mp["p"], mp["q"])
    br2, br3, fac1, fac2 = check_structure(mp, gam, u, w, pw, qw, "sympy")
    r["factor_p_plus_2gamma"] = fac1
    r["factor_q_plus_gamw"] = fac2

    if mp["components"] is not None:
        comps = [s_parse(s) for s in mp["components"]]
        f1, f2, f3 = comps
        r["identity_f2_f3"] = sp.expand(f2 * f3 - (pw + 2 * gam)) == 0
        r["identity_f1_f3sq"] = sp.expand(f1 * f3 ** 2 - (qw + gam * w)) == 0
        r["identity_f3_gam_x"] = sp.expand(f3 - gam * X) == 0
        images = []
        for pt in mp["points"]:
            subs = {X: S(pt[0]), Y: S(pt[1]), Z: S(pt[2])}
            images.append([str(c.subs(subs)) for c in comps])
        r["images"] = images
        image_str = [str(v) for v in mp["image"]]
        r["collision_ok"] = all(im == image_str for im in images)
        r["points_distinct"] = len(set(mp["points"])) == len(mp["points"])
    else:
        # Route 1: brackets divided by powers of x (mirrors Engine O).
        g1 = sp.expand(gam * X)
        g2 = s_div_xn(br2, 1)
        g3 = s_div_xn(br3, 2)
        # Route 2: independent -- direct rational-function cancellation of
        # (p+2*gamma)/(gamma*x) and (q+gamma*w)/(gamma*x)^2.  The result must
        # be a polynomial (denominator 1) and must equal the bracket route.
        g2c = sp.cancel((pw + 2 * gam) / (gam * X))
        g3c = sp.cancel((qw + gam * w) / (gam * X) ** 2)
        n2, d2 = sp.fraction(g2c)
        n3, d3 = sp.fraction(g3c)
        r["route2_g2_cancel_ok"] = (d2 == 1 and sp.expand(n2 - g2) == 0)
        r["route2_g3_cancel_ok"] = (d3 == 1 and sp.expand(n3 - g3) == 0)
        comps = [g1, g2, g3]
        printed = s_parse(mp["g1_printed"])
        r["g1_matches_printed"] = sp.expand(g1 - printed) == 0

    jac = sp.Matrix(comps).jacobian([X, Y, Z])
    det = sp.expand(jac.det())
    r["det"] = str(det)
    r["det_ok"] = sp.simplify(det - S(mp["det"])) == 0
    r["degrees"] = [int(sp.Poly(c, X, Y, Z).total_degree()) for c in comps]
    r["degrees_ok"] = tuple(r["degrees"]) == tuple(mp["degrees"])
    return r, comps


def cross_engine(mp, comps_own, comps_sym):
    """Term-by-term comparison of the two engines' polynomials."""
    out = {"components_equal": True}
    for idx, (a, b) in enumerate(zip(comps_own, comps_sym)):
        same = bool(sp.expand(po_to_sympy(a) - b) == 0)
        out["component_%d_equal" % idx] = same
        out["components_equal"] = out["components_equal"] and same
    # Compare determinants too.
    jo = [[po_deriv(comps_own[i], j) for j in range(3)] for i in range(3)]
    do = po_to_sympy(po_det3(jo))
    js = sp.Matrix(comps_sym).jacobian([X, Y, Z])
    ds = sp.expand(js.det())
    out["det_equal"] = bool(sp.expand(do - ds) == 0)
    return out


# ===========================================================================
# Self-test
# ===========================================================================

def run_selftest():
    checks = []

    def ck(name, cond):
        checks.append((name, bool(cond)))

    # -- parser ------------------------------------------------------------
    ck("parser_const_fraction", parse_expr("1/2") == po_const(Q(1, 2)))
    ck("parser_terms",
       parse_expr("x*y**2 + 3*x + 1/2")
       == {(1, 2, 0): Q(1), (1, 0, 0): Q(3), (0, 0, 0): Q(1, 2)})
    ck("parser_paren_pow",
       parse_expr("(1 + x*y)**2")
       == {(0, 0, 0): Q(1), (1, 1, 0): Q(2), (2, 2, 0): Q(1)})
    ck("parser_unary_minus_pow", parse_expr("-x**2*y") == {(2, 1, 0): Q(-1)})
    ck("parser_frac_div", parse_expr("3/8*x") == {(1, 0, 0): Q(3, 8)})
    ck("parser_rejects_unknown_var",
       _raises(lambda: parse_expr("x + q")))

    # -- algebra -----------------------------------------------------------
    ck("mul_square",
       parse_expr("(x + y)*(x + y)")
       == parse_expr("x**2 + 2*x*y + y**2"))
    ck("deriv_rule",
       po_deriv(parse_expr("x**2*y"), 0) == parse_expr("2*x*y"))
    # Rendering regression guards: a constant must never pick up a stray "1".
    ck("po_str_constant", po_str(po_const(-2)) == "-2")
    ck("po_str_mixed", po_str(parse_expr("2*x + 1")) == "2x + 1")
    ck("deriv_wrt_z", po_deriv(parse_expr("x**3*z"), 2) == parse_expr("x**3"))

    # -- determinants ------------------------------------------------------
    ident = [[po_const(1) if i == j else ZERO_P for j in range(3)]
             for i in range(3)]
    ck("det_identity", po_det3(ident) == po_const(1))
    swap = [[ZERO_P, po_const(1), ZERO_P],
            [po_const(1), ZERO_P, ZERO_P],
            [ZERO_P, ZERO_P, po_const(1)]]
    ck("det_swap_is_minus1", po_det3(swap) == po_const(-1))
    diag_c = [[po_const(2), ZERO_P, ZERO_P],
              [ZERO_P, po_const(3), ZERO_P],
              [ZERO_P, ZERO_P, po_const(-5)]]
    ck("det_const_diag", po_det3(diag_c) == po_const(-30))
    diag_v = [[parse_expr("x"), ZERO_P, ZERO_P],
              [ZERO_P, parse_expr("y"), ZERO_P],
              [ZERO_P, ZERO_P, parse_expr("z")]]
    ck("det_var_diag", po_det3(diag_v) == parse_expr("x*y*z"))

    # -- hand-computed fixtures for F (arithmetic worked out by hand; see
    #    README "Hand fixtures"): -------------------------------------------
    comps = [parse_expr(s) for s in F_COMPONENTS]
    ck("F_hand_P1",
       tuple(po_eval(c, F_POINTS[0]) for c in comps) == F_IMAGE)
    ck("F_hand_P2",
       tuple(po_eval(c, F_POINTS[1]) for c in comps) == F_IMAGE)
    ck("F_hand_P3",
       tuple(po_eval(c, F_POINTS[2]) for c in comps) == F_IMAGE)

    # -- non-Keller map must be flagged ------------------------------------
    H = [parse_expr("x"), parse_expr("x*y"), parse_expr("z")]
    jh = [[po_deriv(H[i], j) for j in range(3)] for i in range(3)]
    dh = po_det3(jh)
    ck("nonconstant_det_detected", dh == {(1, 0, 0): Q(1)})

    # -- Sympy parity on a small case --------------------------------------
    if _SYMPY_OK:
        ck("sympy_det_swap",
           sp.Matrix([[0, 1, 0], [1, 0, 0], [0, 0, 1]]).det() == -1)
        ck("sympy_parses_F",
           sp.expand(s_parse(F_COMPONENTS[2]) - (2 * X - 3 * X ** 2 * Y
                                                 - X ** 3 * Z)) == 0)
        Hs = [X, X * Y, Z]
        ck("engines_agree_on_nonkeller",
           s_components_equal(
               sp.Matrix(Hs).jacobian([X, Y, Z]).det(), X))
    else:
        ck("sympy_importable", False)

    return checks


def _raises(fn):
    try:
        fn()
    except Exception:
        return True
    return False


# ===========================================================================
# Main
# ===========================================================================

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Exact two-engine verification of the 2026 Jacobian "
                    "conjecture counterexamples.")
    ap.add_argument("--map", choices=["all", "alpoge", "gao"], default="all")
    ap.add_argument("--out", default=os.path.join("results",
                                                   "verification_report.json"))
    ap.add_argument("--selftest", action="store_true",
                    help="run the self-test only")
    args = ap.parse_args(argv)

    t_start = time.time()
    print("jacobian_verify %s  (python %s)" % (__version__,
                                               sys.version.split()[0]))

    # ---- self-test -------------------------------------------------------
    st_checks = run_selftest()
    st_failed = [n for n, ok in st_checks if not ok]
    for name, ok in st_checks:
        print("  [%s] selftest.%s" % ("OK" if ok else "FAIL", name))
    if st_failed:
        print("SELFTEST FAILED (%d/%d): %s"
              % (len(st_failed), len(st_checks), ", ".join(st_failed)))
        print("verdict: TOOL_UNTRUSTED (exit 2)")
        return 2
    print("selftest passed (%d checks)" % len(st_checks))

    if args.selftest:
        print("SELFTEST PASSED (exit 0)")
        return 0

    if not _SYMPY_OK:
        print("sympy unavailable: %s" % _SYMPY_ERR)
        print("verdict: TOOL_UNTRUSTED (exit 2)")
        return 2
    print("sympy %s" % sp.__version__)

    # ---- per-map checks --------------------------------------------------
    keys = ["alpoge", "gao"] if args.map == "all" else [args.map]
    results = {}
    claims = []
    failures = []

    def claim(desc, ok):
        claims.append({"claim": desc, "status": "VERIFIED" if ok
                       else "NOT VERIFIED"})
        if not ok:
            failures.append(desc)

    for key in keys:
        mp = MAPS[key]
        mid = mp["id"]
        print("\n=== %s ===" % mid)
        ro, comps_o = run_own(mp)
        rs, comps_s = run_sympy(mp)
        xr = cross_engine(mp, comps_o, comps_s)
        results[mid] = {"own": ro, "sympy": rs, "cross_engine": xr}

        # Factorization claims (Gao's sweep data) -- both engines.
        claim("%s: p(w)+2*gamma == gamma*BR2 (own)" % mid,
              ro["factor_p_plus_2gamma"])
        claim("%s: p(w)+2*gamma == gamma*BR2 (sympy)" % mid,
              rs["factor_p_plus_2gamma"])
        claim("%s: q(w)+gamma*w == gamma^2*BR3 (own)" % mid,
              ro["factor_q_plus_gamw"])
        claim("%s: q(w)+gamma*w == gamma^2*BR3 (sympy)" % mid,
              rs["factor_q_plus_gamw"])

        if mp["components"] is not None:
            # Transcribed components vs sweep structure.
            claim("%s: f2*f3 == p+2*gamma (own)" % mid, ro["identity_f2_f3"])
            claim("%s: f2*f3 == p+2*gamma (sympy)" % mid,
                  rs["identity_f2_f3"])
            claim("%s: f1*f3^2 == q+gamma*w (own)" % mid,
                  ro["identity_f1_f3sq"])
            claim("%s: f1*f3^2 == q+gamma*w (sympy)" % mid,
                  rs["identity_f1_f3sq"])
            claim("%s: f3 == gamma*x (own)" % mid, ro["identity_f3_gam_x"])
            claim("%s: f3 == gamma*x (sympy)" % mid, rs["identity_f3_gam_x"])
            claim("%s: three points collide at (-1/4,0,0) (own)" % mid,
                  ro["collision_ok"])
            claim("%s: three points collide at (-1/4,0,0) (sympy)" % mid,
                  rs["collision_ok"])
            claim("%s: the three points are pairwise distinct" % mid,
                  ro["points_distinct"])
        else:
            claim("%s: g1 matches the printed expansion" % mid,
                  ro.get("g1_matches_printed"))
            claim("%s: g1 matches the printed expansion (sympy)" % mid,
                  rs.get("g1_matches_printed"))
            claim("%s: route-2 cancellation reproduces g2/g3 (sympy)" % mid,
                  rs.get("route2_g2_cancel_ok") and
                  rs.get("route2_g3_cancel_ok"))

        claim("%s: det J == %s (own)" % (mid, str(mp["det"])),
              ro["det_ok"])
        claim("%s: det J == %s (sympy)" % (mid, str(mp["det"])),
              rs["det_ok"])
        claim("%s: component degrees == %s (own)"
              % (mid, str(mp["degrees"])), ro["degrees_ok"])
        claim("%s: component degrees == %s (sympy)"
              % (mid, str(mp["degrees"])), rs["degrees_ok"])
        claim("%s: both engines agree term-by-term (components + det)" % mid,
              xr["components_equal"] and xr["det_equal"])

        print("  det (own)   = %s" % ro["det"])
        print("  det (sympy) = %s" % rs["det"])
        print("  degrees (own/sympy) = %s / %s"
              % (ro["degrees"], rs["degrees"]))
        if mp["points"] is not None:
            print("  images (own) = %s" % ro["images"])

    # ---- verdict ---------------------------------------------------------
    timing = time.time() - t_start
    if failures:
        verdict = "CLAIM_NOT_REPRODUCED"
        code = 1
    else:
        verdict = "ALL_PINNED_CLAIMS_VERIFIED"
        code = 0

    report = {
        "tool": "jacobian_verify.py",
        "version": __version__,
        "env": {
            "python": sys.version.split()[0],
            "sympy": sp.__version__,
        },
        "sources": SOURCES,
        "maps": keys,
        "selftest": {"passed": True, "checks": len(st_checks)},
        "results": results,
        "claims": claims,
        "failures": failures,
        "verdict": verdict,
        "timing_s": round(timing, 3),
    }
    out_dir = os.path.dirname(args.out)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")

    print("\n--- claims (%d) ---" % len(claims))
    for c in claims:
        print("  [%s] %s" % ("OK" if c["status"] == "VERIFIED" else "FAIL",
                             c["claim"]))
    print("\nverdict: %s (exit %d)" % (verdict, code))
    print("timing: %.3f s" % timing)
    print("written: %s" % args.out)
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print("INTERNAL ERROR: %s" % exc)
        print("verdict: TOOL_UNTRUSTED (exit 2)")
        sys.exit(2)
