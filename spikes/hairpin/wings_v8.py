"""SPIKE v8 wing set: cambered, inverted sections tuned to a 2026-ish downforce level (ASSUMPTIONS, see TARGET).

Single element per wing stands in for main plane + flap(s): a NACA 4-digit mean line with NEGATIVE camber (downforce).
TARGET ClA (m^2, downforce coefficient x area): front 0.90, rear 0.75 (corner / Z-mode).
Reasoning, not data: 2026 rules cut downforce ~30% vs 2022-25 (FIA target); wing split is an assumption (floor ~50%+).
"""
import numpy as np

from hairpin_trails import g

# name, x ahead of car centre, half span, chord, height above ground (m), pitch deg (neg = nose down), camber, camber pos
# pitch tuned with PteraSoftware steady VLM in ground effect (raised front tips, both wings): front 0.92, rear 0.72 m^2
# front: outer 0.35 m of each side rises 0.15 m (2026 shape, ends lifted) -> SECTIONS gives (dy, dz) steps from the centre
WINGS = [("front", 2.75, 0.95, 0.45, 0.10, -1.5, -0.08, 0.45),
         ("rear", -2.45, 0.50, 0.55, 0.80, -20.0, -0.12, 0.50)]
SECTIONS = {"front": [(0.60, 0.0), (0.35, 0.15)], "rear": [(0.50, 0.0)]}
SPACING = "cosine"                 # spanwise panel spacing per section
TARGET = {"front": 0.90, "rear": 0.75}


def naca_outline(m, p, t=0.10, n=60):
    """Selig-order outline (upper TE -> LE -> lower TE) of a NACA 4-digit section; m < 0 gives downforce camber."""
    b = 0.5 * (1 - np.cos(np.linspace(0, np.pi, n)))
    yt = 5 * t * (0.2969 * np.sqrt(b) - 0.1260 * b - 0.3516 * b ** 2 + 0.2843 * b ** 3 - 0.1036 * b ** 4)
    yc = np.where(b < p, m / p ** 2 * (2 * p * b - b ** 2), m / (1 - p) ** 2 * (1 - 2 * p + 2 * p * b - b ** 2))
    dy = np.where(b < p, 2 * m / p ** 2 * (p - b), 2 * m / (1 - p) ** 2 * (p - b))
    th = np.arctan(dy)
    up = np.c_[b - yt * np.sin(th), yc + yt * np.cos(th)]
    lo = np.c_[b + yt * np.sin(th), yc - yt * np.cos(th)]
    return np.r_[up[::-1], lo[1:]]


def airfoil(m, p):
    return g.airfoil.Airfoil(name=f"inv{abs(m):.2f}_{p:.2f}", outline_A_lp=naca_outline(m, p))


def install(v4):
    """Swap these wings into the hairpin_v4 pipeline (geometry tuples + cambered airfoils)."""
    v4.WINGS[:] = [w[:6] for w in WINGS]
    cam = {w[0]: (w[6], w[7]) for w in WINGS}

    def wing_geom(name, x, half, chord, z, pitch):
        af = airfoil(*cam[name])
        steps = [(0.0, 0.0)] + SECTIONS[name]
        n_sp = [max(2, round(v4.N_SPAN * dy / half)) for dy, _ in SECTIONS[name]] + [None]
        xs = [g.wing_cross_section.WingCrossSection(
            airfoil=af, num_spanwise_panels=n, chord=chord, Lp_Wcsp_Lpp=(0.0, dy, dz),
            control_surface_symmetry_type="symmetric", spanwise_spacing=SPACING if n else None) for (dy, dz), n in zip(steps, n_sp)]
        return g.wing.Wing(wing_cross_sections=xs, name=name, Ler_Gs_Cgs=(-x, 0.0, z),
                           angles_Gs_to_Wn_ixyz=(0.0, pitch, 0.0), symmetric=True, symmetryNormal_G=(0.0, 1.0, 0.0),
                           symmetryPoint_G_Cg=(0.0, 0.0, 0.0), num_chordwise_panels=5, chordwise_spacing="uniform")
    v4.wing_geom = wing_geom
