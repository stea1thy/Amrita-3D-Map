"""White marble Saraswati statue for the AB-1 Lotus fountain (pipeline/refs/ab1_irl_statue_front.webp).

The Goddess sits on a two-tier open lotus, playing the veena: the large resonator rests on her right thigh, the neck rises
diagonally to her left ending in a curled scroll with a second gourd hanging below it. Four arms: front right plucks the
strings, front left holds the neck, rear right is raised (japa mala), rear left holds a palm-leaf book. Tall crown
(kireeta) with an arched top and finial. Proportions are measured from the front photo: total height ~4.0 m, lotus
~1.05 m tall and ~4 m wide (as wide as the statue is tall).

Local frame: X = viewer's right when facing the statue (world +X), Y = into the statue (world +Y / North),
Z = up from the lotus base. The statue faces South (-Y), toward the entry road.
"""

from __future__ import annotations

import math
from typing import Any

import bmesh

Vec3 = tuple[float, float, float]
RGBA = tuple[float, float, float, float]


class _Builder:
    def __init__(
        self,
        bm: bmesh.types.BMesh,
        col_layer: Any,
        origin: Vec3,
        offset_xyz: Vec3,
        scale: float = 1.0,
    ) -> None:
        self.scale = scale
        self.bm = bm
        self.col = col_layer
        self.origin = origin
        self.off = offset_xyz

    def v(self, p: Vec3) -> bmesh.types.BMVert:
        ox, oy, oz = self.origin
        k = self.scale
        return self.bm.verts.new((ox + k * p[0] - self.off[0], oy + k * p[1] - self.off[1], oz + k * p[2] - self.off[2]))

    def face(self, verts: tuple[bmesh.types.BMVert, ...], rgba: RGBA, smooth: bool) -> None:
        try:
            f = self.bm.faces.new(verts)
        except ValueError:
            return
        f.smooth = smooth
        for loop in f.loops:
            loop[self.col] = rgba

    def ellipsoid(self, c: Vec3, r: Vec3, segs: int, rings: int, rgba: RGBA, smooth: bool = True) -> None:
        top = self.v((c[0], c[1], c[2] + r[2]))
        bot = self.v((c[0], c[1], c[2] - r[2]))
        rows: list[list[bmesh.types.BMVert]] = []
        for i in range(1, rings):
            phi = math.pi * i / rings
            s, zc = math.sin(phi), math.cos(phi)
            rows.append([
                self.v((c[0] + r[0] * s * math.cos(2 * math.pi * j / segs),
                        c[1] + r[1] * s * math.sin(2 * math.pi * j / segs),
                        c[2] + r[2] * zc))
                for j in range(segs)
            ])
        for j in range(segs):
            k = (j + 1) % segs
            self.face((top, rows[0][j], rows[0][k]), rgba, smooth)
            self.face((bot, rows[-1][k], rows[-1][j]), rgba, smooth)
            for a in range(len(rows) - 1):
                up, lo = rows[a], rows[a + 1]
                self.face((lo[j], lo[k], up[k], up[j]), rgba, smooth)

    def limb(self, p0: Vec3, p1: Vec3, r0: float, r1: float, segs: int, rgba: RGBA,
             cap0: bool = False, cap1: bool = False, smooth: bool = True) -> None:
        d = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        ln = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2) or 1e-6
        d = (d[0] / ln, d[1] / ln, d[2] / ln)
        a = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (1.0, 0.0, 0.0)
        u = (d[1] * a[2] - d[2] * a[1], d[2] * a[0] - d[0] * a[2], d[0] * a[1] - d[1] * a[0])
        ul = math.sqrt(u[0] ** 2 + u[1] ** 2 + u[2] ** 2)
        u = (u[0] / ul, u[1] / ul, u[2] / ul)
        w = (d[1] * u[2] - d[2] * u[1], d[2] * u[0] - d[0] * u[2], d[0] * u[1] - d[1] * u[0])

        def ring(p: Vec3, r: float) -> list[bmesh.types.BMVert]:
            out = []
            for j in range(segs):
                t = 2 * math.pi * j / segs
                ct, st = math.cos(t), math.sin(t)
                out.append(self.v((p[0] + r * (ct * u[0] + st * w[0]),
                                   p[1] + r * (ct * u[1] + st * w[1]),
                                   p[2] + r * (ct * u[2] + st * w[2]))))
            return out

        b, t_ = ring(p0, r0), ring(p1, r1)
        for j in range(segs):
            k = (j + 1) % segs
            self.face((b[j], b[k], t_[k], t_[j]), rgba, smooth)
        if cap1:
            cv = self.v(p1)
            for j in range(segs):
                self.face((cv, t_[j], t_[(j + 1) % segs]), rgba, smooth)
        if cap0:
            cv = self.v(p0)
            for j in range(segs):
                self.face((cv, b[(j + 1) % segs], b[j]), rgba, smooth)

    def loft(self, rings: list[tuple[Vec3, float, float]], segs: int, rgba: RGBA, smooth: bool = True) -> None:
        """Horizontal elliptical cross-sections (centre, rx, ry) stacked bottom -> top, capped both ends."""
        loops = []
        for c, rx, ry in rings:
            loops.append([
                self.v((c[0] + rx * math.cos(2 * math.pi * j / segs), c[1] + ry * math.sin(2 * math.pi * j / segs), c[2]))
                for j in range(segs)
            ])
        for a in range(len(loops) - 1):
            lo, up = loops[a], loops[a + 1]
            for j in range(segs):
                k = (j + 1) % segs
                self.face((lo[j], lo[k], up[k], up[j]), rgba, smooth)
        top_c, bot_c = self.v(rings[-1][0]), self.v(rings[0][0])
        for j in range(segs):
            k = (j + 1) % segs
            self.face((top_c, loops[-1][j], loops[-1][k]), rgba, smooth)
            self.face((bot_c, loops[0][k], loops[0][j]), rgba, smooth)

    def petal(self, theta: float, half: float, base: tuple[float, float], belly: tuple[float, float],
              tip: tuple[float, float], bulge: float, rgba_out: RGBA, rgba_in: RGBA) -> None:
        """Broad cupped lotus petal with rounded shoulders and a short point (outer + inner skin).
        base/belly/tip are (radius, z); `half` is the half-angle of the petal at its widest."""

        def p(r: float, ang: float, z: float) -> Vec3:
            return (r * math.cos(ang), r * math.sin(ang), z)

        sh_r = belly[0] + 0.72 * (tip[0] - belly[0])
        sh_z = belly[1] + 0.68 * (tip[1] - belly[1])
        for skin, inset in ((0, 0.0), (1, 0.06)):
            B = self.v(p(base[0] - inset, theta, base[1]))
            L = self.v(p(belly[0] - inset, theta - half, belly[1]))
            R = self.v(p(belly[0] - inset, theta + half, belly[1]))
            C = self.v(p(belly[0] + bulge - inset, theta, belly[1] + 0.04))
            SL = self.v(p(sh_r - inset, theta - 0.62 * half, sh_z))
            SR = self.v(p(sh_r - inset, theta + 0.62 * half, sh_z))
            T = self.v(p(tip[0] + 0.03 - inset, theta, tip[1]))
            tris = ((B, R, C), (B, C, L), (C, R, SR), (C, SR, T), (C, T, SL), (C, SL, L))
            for tri in tris:
                self.face(tri if skin == 0 else (tri[0], tri[2], tri[1]), rgba_out if skin == 0 else rgba_in, False)


def append_saraswati_statue(
    bm: bmesh.types.BMesh,
    col_layer: Any,
    origin: Vec3,
    marble: RGBA,
    marble_shade: RGBA,
    offset_xyz: Vec3 = (0.0, 0.0, 0.0),
    scale: float = 1.0,
) -> None:
    """Emit the seated four-armed Saraswati with veena on a two-tier lotus. `origin` = lotus base centre (world);
    `scale` = 1.0 gives a 4.0 m statue."""
    s = _Builder(bm, col_layer, origin, offset_xyz, scale)
    m, sh = marble, marble_shade

    # ---- Lotus (two rows of 10 pointed petals around a drum + seat) ----
    s.limb((0, 0, 0.0), (0, 0, 0.32), 1.18, 1.38, 12, sh, smooth=False)
    s.limb((0, 0, 0.30), (0, 0, 0.95), 1.32, 1.32, 12, m, cap1=True, smooth=False)
    for k in range(10):
        th = -0.5 * math.pi + k * (2 * math.pi / 10)
        s.petal(th, 0.34, (1.05, 0.06), (1.84, 0.48), (2.00, 1.00), 0.10, m, sh)
    for k in range(10):
        th = -0.5 * math.pi + (k + 0.5) * (2 * math.pi / 10)
        s.petal(th, 0.34, (0.85, 0.32), (1.46, 0.76), (1.52, 1.16), 0.08, m, sh)

    # ---- Seated body ----
    s.ellipsoid((0.0, 0.05, 1.18), (1.10, 0.80, 0.33), 12, 6, m)  # lap / saree spread on the lotus
    s.ellipsoid((-0.95, -0.36, 1.17), (0.44, 0.40, 0.24), 10, 5, m)  # right leg folded across the seat
    s.ellipsoid((0.70, -0.46, 1.30), (0.33, 0.44, 0.29), 10, 5, m)  # left knee raised
    s.ellipsoid((0.0, -0.62, 0.98), (0.62, 0.22, 0.20), 10, 4, sh)  # saree pleats falling over the petals
    s.loft([
        ((0.0, 0.10, 1.38), 0.42, 0.32),
        ((0.0, 0.08, 1.76), 0.35, 0.27),  # waist
        ((0.0, 0.06, 2.16), 0.45, 0.33),  # bust
        ((0.0, 0.08, 2.54), 0.52, 0.30),  # shoulders
        ((0.0, 0.10, 2.70), 0.30, 0.21),
        ((0.0, 0.10, 2.80), 0.12, 0.12),
    ], 12, m)
    s.limb((0.0, 0.10, 2.74), (0.0, 0.08, 2.96), 0.12, 0.11, 8, m)  # neck
    s.limb((0.0, 0.03, 2.66), (0.0, 0.03, 2.74), 0.27, 0.22, 10, sh, smooth=False)  # necklace collar
    s.ellipsoid((0.0, 0.04, 3.05), (0.17, 0.19, 0.23), 12, 6, m)  # head (face visible below the crown)
    s.ellipsoid((0.0, 0.20, 2.94), (0.22, 0.15, 0.34), 8, 5, m)  # hair falling behind

    # ---- Crown (kireeta): flared drum, dome, arched top band and finial ----
    s.loft([
        ((0.0, 0.07, 3.22), 0.165, 0.17),
        ((0.0, 0.07, 3.36), 0.195, 0.19),
        ((0.0, 0.07, 3.52), 0.18, 0.18),
        ((0.0, 0.07, 3.64), 0.13, 0.13),
    ], 12, m)
    s.ellipsoid((0.0, 0.07, 3.64), (0.13, 0.13, 0.10), 10, 4, m)  # rounded crown top
    s.limb((0.0, 0.07, 3.72), (0.0, 0.07, 3.92), 0.05, 0.02, 6, m, cap1=True)
    s.ellipsoid((0.0, 0.07, 3.96), (0.055, 0.055, 0.065), 6, 4, m)  # finial
    s.limb((0.0, 0.07, 3.21), (0.0, 0.07, 3.27), 0.185, 0.19, 12, sh, smooth=False)  # jewelled crown band
    arc_c, arc_r = (0.0, 0.07, 3.66), 0.15  # small arch standing on top of the crown (photo)
    prev = None
    for i in range(7):
        a = math.radians(i * 30)
        pt = (arc_c[0] + arc_r * math.cos(a), arc_c[1], arc_c[2] + arc_r * math.sin(a) * 1.15)
        if prev is not None:
            s.limb(prev, pt, 0.035, 0.035, 5, m)
        prev = pt

    # ---- Four arms (shoulder -> elbow -> hand) ----
    arms = (
        ((-0.50, 0.15, 2.55), (-0.84, 0.12, 2.00), (-0.86, 0.02, 2.62)),  # rear right, raised (mala)
        ((-0.47, -0.02, 2.50), (-0.80, -0.26, 1.96), (-0.36, -0.56, 1.86)),  # front right, plucking strings
        ((0.50, -0.02, 2.50), (0.80, -0.26, 2.02), (1.00, -0.43, 2.45)),  # front left, holding the neck
        ((0.52, 0.15, 2.50), (0.86, 0.15, 1.96), (0.98, 0.00, 1.62)),  # rear left, holding the book
    )
    for sp, ep, hp in arms:
        s.limb(sp, ep, 0.13, 0.10, 8, m)
        s.limb(ep, hp, 0.10, 0.075, 8, m)
        s.ellipsoid(hp, (0.09, 0.08, 0.11), 8, 4, m)
    s.limb((-0.86, 0.0, 2.70), (-0.83, -0.02, 2.90), 0.035, 0.02, 5, m, cap1=True)  # raised fingers
    s.limb((-0.92, -0.05, 2.62), (-0.95, -0.06, 2.36), 0.025, 0.025, 4, sh)  # mala strand
    s.loft([((1.00, -0.06, 1.46), 0.19, 0.07), ((1.00, -0.06, 1.70), 0.19, 0.07)], 4, sh, smooth=False)  # book

    # ---- Veena ----
    s.ellipsoid((-0.62, -0.46, 1.62), (0.46, 0.38, 0.38), 12, 6, m)  # main resonator on the right thigh
    neck0, neck1 = (-0.30, -0.53, 1.78), (1.76, -0.35, 2.82)
    s.limb(neck0, neck1, 0.11, 0.09, 8, m, cap0=True)
    scroll = ((1.76, -0.35, 2.82), (1.95, -0.33, 2.98), (2.03, -0.32, 2.82), (1.91, -0.32, 2.66))
    for i in range(len(scroll) - 1):
        s.limb(scroll[i], scroll[i + 1], 0.085 - i * 0.012, 0.075 - i * 0.012, 6, m, cap1=(i == len(scroll) - 2))
    s.limb((1.20, -0.40, 2.50), (1.15, -0.38, 2.40), 0.05, 0.05, 6, m)  # gourd stem
    s.ellipsoid((1.12, -0.36, 2.13), (0.30, 0.30, 0.30), 10, 6, m)  # upper gourd (tumba)
