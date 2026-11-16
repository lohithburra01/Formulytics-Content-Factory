"""THROWAWAY SPIKE: PteraSoftware on an F1-like front + rear wing in ground effect.

Free-wake unsteady VLM at 70 m/s, then plots the wake from the top and the side, and a ride-height sweep
of front-wing downforce (steady VLM). Wings only - no floor, body or wheels (the method cannot do those).
"""
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pterasoftware as ps
from pterasoftware import geometry as g, movements as m, operating_point as op, problems as pr

V = 70.0          # m/s (~250 km/h)
H_FW = 0.08       # front wing height above ground, m
PITCH = float(sys.argv[1]) if len(sys.argv) > 1 else 8.0   # wing incidence, deg (sign checked from output)


def wing(name, x, z, half_span, chord, pitch, n_span):
    xs = lambda y, c: g.wing_cross_section.WingCrossSection(
        airfoil=g.airfoil.Airfoil(name="NACA0012"), num_spanwise_panels=n_span if y == 0 else None,
        chord=c, Lp_Wcsp_Lpp=(0.0, y, 0.0), control_surface_symmetry_type="symmetric", spanwise_spacing="cosine" if y == 0 else None)
    return g.wing.Wing(wing_cross_sections=[xs(0, chord), xs(half_span, chord)], name=name,
                       Ler_Gs_Cgs=(x, 0.0, z), angles_Gs_to_Wn_ixyz=(0.0, pitch, 0.0), symmetric=True,
                       symmetryNormal_G=(0.0, 1.0, 0.0), symmetryPoint_G_Cg=(0.0, 0.0, 0.0),
                       num_chordwise_panels=6, chordwise_spacing="uniform")


def car(front_only=False):
    wings = [wing("Front wing", 0.0, 0.0, 0.9, 0.30, PITCH, 12)]
    if not front_only:
        wings.append(wing("Rear wing", 3.4, 0.75, 0.5, 0.35, PITCH, 8))
    return g.airplane.Airplane(wings=wings, name="F1-ish wings")


def oper(h):
    return op.OperatingPoint(vCg__E=V, alpha=0.0, CgP1_E_Eo=(0.0, 0.0, -h),
                             surfaceNormal_E=(0.0, 0.0, 1.0), surfacePoint_E_Eo=(0.0, 0.0, 0.0))


def static_movement(plane, h, num_chords):
    wms = [m.wing_movement.WingMovement(base_wing=w, wing_cross_section_movements=[
        m.wing_cross_section_movement.WingCrossSectionMovement(base_wing_cross_section=x) for x in w.wing_cross_sections])
        for w in plane.wings]
    return m.movement.Movement(
        airplane_movements=[m.airplane_movement.AirplaneMovement(base_airplane=plane, wing_movements=wms)],
        operating_point_movement=m.operating_point_movement.OperatingPointMovement(base_operating_point=oper(h)),
        num_chords=num_chords)


def forces(airplane):
    for attr in ("forces_W", "forces_E", "forces_GP1"):
        if hasattr(airplane, attr):
            return attr, np.asarray(getattr(airplane, attr))
    return "?", np.full(3, np.nan)


# 1) free-wake unsteady run, both wings
plane = car()
solver = ps.unsteady_ring_vortex_lattice_method.UnsteadyRingVortexLatticeMethodSolver(
    unsteady_problem=pr.UnsteadyProblem(movement=static_movement(plane, H_FW, num_chords=30)))
t0 = time.time()
solver.run(prescribed_wake=False, calculate_streamlines=False, show_progress=False)
t_unsteady = time.time() - t0
final = solver.steady_problems[-1].airplanes[0]
name, F = forces(final)
print(f"unsteady free wake: {solver.num_steps} steps, {solver.num_panels} panels, {t_unsteady:.1f} s; final {name} = {F}")

# wake + wing geometry at the last step
wake = np.concatenate([np.asarray(a).reshape(-1, 3) for a in solver.listStackFlwrvp_GP1_CgP1[-1:]], axis=0)
pan = np.asarray(solver.stackCpp_GP1_CgP1).reshape(-1, 3)
print(f"wake points {len(wake)}; panel z range {pan[:, 2].min():.2f}..{pan[:, 2].max():.2f}; wake z range {wake[:, 2].min():.2f}..{wake[:, 2].max():.2f}")

# 2) steady ride-height sweep, front wing alone
hs = np.array([0.03, 0.05, 0.08, 0.12, 0.18, 0.27, 0.4, 0.6, 1.0, 3.0])
Fz = []
t0 = time.time()
for h in hs:
    sp = pr.SteadyProblem(airplanes=[car(front_only=True)], operating_point=oper(h))
    s = ps.steady_ring_vortex_lattice_method.SteadyRingVortexLatticeMethodSolver(steady_problem=sp)
    s.run()
    Fz.append(forces(sp.airplanes[0])[1][2])
t_sweep = time.time() - t0
Fz = np.array(Fz)
print(f"steady sweep {len(hs)} heights in {t_sweep:.1f} s ({1e3 * t_sweep / len(hs):.0f} ms each); Fz:", np.round(Fz, 1))

# 3) pictures
fig, ax = plt.subplots(3, 1, figsize=(11, 13))
for a, (i, j, lab) in zip(ax[:2], [(0, 1, "TOP VIEW  (x along the car, y across)"), (0, 2, "SIDE VIEW  (x along, z up from front wing)")]):
    a.scatter(wake[:, i], wake[:, j], s=2, c=wake[:, 0], cmap="viridis", label="wake vortex points")
    a.scatter(pan[:, i], pan[:, j], s=6, c="red", label="wing panels")
    a.set_title(lab); a.set_aspect("equal"); a.legend(loc="upper right", fontsize=8)
ax[1].axhline(-H_FW, color="k", lw=2); ax[1].text(0, -H_FW - 0.08, "ground", fontsize=8)
ax[2].plot(hs / 0.30, np.abs(Fz), "o-")
ax[2].set_xscale("log"); ax[2].set_xlabel("front wing height / chord"); ax[2].set_ylabel("|vertical force| (N)")
ax[2].set_title("Front wing force vs ride height (steady VLM, inviscid: no stall near the ground)")
fig.suptitle(f"PteraSoftware 5.1 - wings only, {V:.0f} m/s, incidence {PITCH} deg  (unsteady {t_unsteady:.0f} s, sweep {1e3 * t_sweep / len(hs):.0f} ms/case)")
fig.tight_layout()
fig.savefig("pterasoftware_f1_wings.png", dpi=110)
print("saved pterasoftware_f1_wings.png")
