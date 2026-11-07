"""Cheapest drone: ABS-printed airframe around bulk-buyable electronics.

One script makes everything for this aircraft:
  1. sizes the ABS arms so they pass BOTH stiffness models (frame check > 180 Hz, search model > 150 Hz)
  2. writes print files (plate, guards, cradle, drill jig) via ../Variants/variant_frames.py
  3. builds an assembly CAD with every part placed (STEP) + an exploded STEP, and renders PNG views
  4. computes the PHYSICAL MODEL from the CAD solids: mass, CG and inertia tensor per part and in total
  5. writes the ArduPilot SITL frame model from that physical model (used by 08_*/GroundTools/sitl_drop_test.py)

Change CONFIG (board / motor / prop / pack) and re-run.  Needs cadquery, shapely, ezdxf, matplotlib, numpy.
Outputs in this folder: CHEAP_PrintFiles/ (print files + checks.json), Cheapest_Assembly.step,
Cheapest_Assembly_Exploded.step, render_*.png, physical_model.json, sitl_cheapest.json
"""
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import cadquery as cq
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "Variants"))
import variant_frames as V  # noqa: E402

G0 = 9.80665
RHO_ABS = 1.04e-3

# ------------------------------------------------------------------ parts (bulk-buyable; see README for sources)
CONFIG = {
    # MicoAir743v2-AIO-35A: H743 2 MB (runs drop_trigger.lua), 2-6S, Bluejay 35 A, BDShot, microSD, 25.5 mm M3 mount,
    # 36x36x8 mm, 10 g, $64.99 (micoair.com, ArduPilot target MicoAir743v2 >= 4.6). Same frame takes the 30x30 Flywoo
    # GOKU F405 HD 1-2S AIO v2 / CrazyF405HD (bulk, no Lua) on the same 25.5 mm holes (M2 screws in the 3.2 mm holes).
    "board": {"name": "MicoAir743v2-AIO-35A", "target": "MicoAir743v2", "pitch": 25.5, "hole": 3.2,
              "size": (36.0, 36.0), "pcb_t": 1.6, "comp_h": 6.4, "mass_g": 10.0, "standoff_h": 4.0},
    "rx": {"name": "RadioMaster RP1 V2 ELRS (UART)", "mass_g": 2.2, "size": (14.0, 11.0, 3.5)},
    # MTF-01: 29.3 x 17 x 14.5 mm, 4.5 g, holes 24.3 x 12 mm (micoair.com). The first model used 7 mm (wrong).
    "flow": {"name": "MicoAir MTF-01 (flow + ToF height truth)", "mass_g": 4.5, "size": (29.3, 17.0, 14.5), "fitted": True},
    "motor": {"name": "BetaFPV 1103 10500KV", "mass_g": 3.5, "bell_d": 13.5, "bell_h": 8.5, "base_h": 1.5,
              "pcd": 6.6, "holes": 3, "hole_d": 1.6, "label": "M1.4"},
    "prop": {"name": "GF 2218-3", "d": 2.2 * 25.4, "blades": 3, "mass_g": 1.0},
    "pack": {"name": "CNHL MiniStar 2S 650 70C", "dims": (58.0, 30.0, 15.0), "mass_g": 49.0},
    "guard_wall": 2.4,          # ABS guard: thicker than the 2.0 mm TPU ring because ABS is less tough
    "extra_mass_g": {"wiring + XT30 pigtail + cap": 4.5, "screws, nuts, standoffs": 4.0, "strap": 1.0},
}


def r_guard_out():
    return CONFIG["prop"]["d"] / 2 + V.PROP_CLR + CONFIG["guard_wall"]


def motor_radius():
    """Smallest motor radius that fits: guards 2 mm apart, guard 2 mm clear of the board corner."""
    b = CONFIG["board"]
    r = r_guard_out()
    return round(max((2 * r + 2.0) / math.sqrt(2), math.hypot(*b["size"]) / 2 + r + 2.0), 2)


def modes(R, core, w, t, guard_g):
    """(frame-check flap Hz, torsion Hz, search-model Hz, tilt deg) for an ABS arm. Same formulas as the two models."""
    E, Gm = V.MATERIALS["abs_print"]["E"], V.MATERIALS["abs_print"]["G"]
    mo, pr = CONFIG["motor"], CONFIG["prop"]
    F = full_thrust_g() * G0 / 1000
    l = R - core / 2 * math.sqrt(2) + 3.0
    I = w * t ** 3 / 12
    m_tip = mo["mass_g"] + pr["mass_g"] + guard_g + 0.5
    f_flap = math.sqrt(3 * E * I / l ** 3 * 1e3 / (m_tip * 1e-3)) / (2 * math.pi)
    J = w * t ** 3 / 3 * (1 - 0.63 * t / w)
    ri = pr["d"] / 2 + V.PROP_CLR
    I_tip = guard_g * 1e-3 * ((ri + 1) * 1e-3) ** 2 / 2 + mo["mass_g"] * 1e-3 * (mo["bell_d"] / 2e3) ** 2 / 2
    f_t = math.sqrt(Gm * J / l * 1e-3 / I_tip) / (2 * math.pi)
    # search model (evolve_drone.evaluate): L = R - 15, tip = motor + 1 g + guard, + 24 % of a quarter frame
    L = (R - 15.0) / 1000
    Es, ws, ts = E * 1e6, w / 1000, t / 1000
    Is = ws * ts ** 3 / 12
    frame_g = ((3.6 * 3.6) + 4 * (L * 100) * (ws * 100) + 4 * 1.3 ** 2) * (ts * 100) * 1.04
    f_s = math.sqrt(3 * Es * Is / L ** 3 / ((mo["mass_g"] + 1.0 + guard_g) / 1000 + 0.24 * frame_g / 1000 / 4)) / (2 * math.pi)
    tilt = math.degrees(F * l ** 2 / (2 * E * I))
    return f_flap, f_t, f_s, tilt


def full_thrust_g():
    _, _, full = V.catalog_parts(variant(motor_radius(), 6.0, 10.0))
    return full["thrust_g"]


def variant(R, t, w):
    b, mo, pr, pk = CONFIG["board"], CONFIG["motor"], CONFIG["prop"], CONFIG["pack"]
    return V.Variant(
        key="CHEAP_PrintFiles", title="Cheapest drone (ABS, bulk electronics)", cost_usd=0.0, pareto_ref="cheapest_drone.py",
        material="abs_print", plate_t=t, motor_r=R, arm_w=w, core=max(34.0, b["pitch"] + 2 * 4.3), fillet=4.0,
        stack_pitch=b["pitch"], stack_hole=b["hole"], stack_label=f"AIO M2 {b['pitch']}x{b['pitch']}",
        motor=mo["name"], prop=pr["name"], prop_d=pr["d"], motor_pcd=mo["pcd"], motor_holes=mo["holes"],
        motor_hole_d=mo["hole_d"], motor_hole_label=mo["label"], shaft_clr=3.5, pad_d=17.0, ear_r=9.5,
        bell_d=mo["bell_d"], guard_kind="ring", guard_h=19.0, esc_board=b["size"], fc_board=b["size"],
        pack_name=pk["name"], pack=pk["dims"], reuse_revs_jig=False, guard_material="ABS", guard_wall=CONFIG["guard_wall"],
        notes=["ABS on the Stratasys F170/F370: solid fill, printed flat",
               "ABS guards are less tough than TPU: run T9 (guard drop test) before trials; TPU rings are the fallback"])


def size_arm():
    """Lightest (t, w) that passes: frame check flap & torsion >= 180 Hz, search model >= 150 Hz, tilt < 1 deg."""
    R = motor_radius()
    guard_g = 10.3 * RHO_ABS / V.RHO_GUARD["TPU"] * (CONFIG["guard_wall"] / 2.0)      # scaled from the 2.0 mm TPU ring
    best = None
    for t in (5.0, 6.0, 7.0, 8.0):
        for w in np.arange(8.0, 16.01, 0.5):
            ff, ft, fs, tilt = modes(R, max(34.0, CONFIG["board"]["pitch"] + 8.6), w, t, guard_g)
            if min(ff, ft) >= 180 and fs >= 150 and tilt < 1.0:
                area = t * w
                if best is None or area < best[0]:
                    best = (area, t, float(w), ff, ft, fs, tilt)
    _, t, w, ff, ft, fs, tilt = best
    return R, t, w, {"frame_flap_Hz": round(ff), "frame_torsion_Hz": round(ft), "search_model_Hz": round(fs),
                     "tilt_deg": round(tilt, 3), "guard_mass_est_g": round(guard_g, 2)}


# ------------------------------------------------------------------ assembly parts (envelopes with real masses)
def motor_solid():
    mo = CONFIG["motor"]
    base = cq.Workplane("XY").circle(mo["bell_d"] / 2 - 0.5).extrude(mo["base_h"])
    bell = cq.Workplane("XY").workplane(offset=mo["base_h"]).circle(mo["bell_d"] / 2).extrude(mo["bell_h"])
    shaft = cq.Workplane("XY").workplane(offset=mo["base_h"] + mo["bell_h"]).circle(0.75).extrude(4.0)
    return base.union(bell).union(shaft)


def prop_solid():
    pr, mo = CONFIG["prop"], CONFIG["motor"]
    z = mo["base_h"] + mo["bell_h"] + 0.5
    hub = cq.Workplane("XY").workplane(offset=z).circle(2.75).circle(0.8).extrude(4.5)   # 1.6 mm bore on the 1.5 mm shaft
    p = hub
    for k in range(pr["blades"]):
        blade = (cq.Workplane("XY").workplane(offset=z + 1.5).center(pr["d"] / 4 + 1.2, 0)
                 .rect(pr["d"] / 2 - 2.4, 6.5).extrude(1.0)
                 .rotate((0, 0, 0), (0, 0, 1), 360.0 / pr["blades"] * k))
        p = p.union(blade)
    return p, z + 2.0


def board_solids():
    b = CONFIG["board"]
    sx, sy = b["size"]
    z0 = b["standoff_h"]
    pcb = cq.Workplane("XY").workplane(offset=z0).rect(sx, sy).extrude(b["pcb_t"])
    for dx in (-1, 1):
        for dy in (-1, 1):
            pcb = pcb.cut(cq.Workplane("XY").workplane(offset=z0 - 1).center(dx * b["pitch"] / 2, dy * b["pitch"] / 2)
                          .circle(b["hole"] / 2).extrude(b["pcb_t"] + 2))
    comps = (cq.Workplane("XY").workplane(offset=z0 + b["pcb_t"]).rect(sx - 8, sy - 8).extrude(b["comp_h"]))
    for dx in (-1, 1):   # no components inside the mounting-hole keep-outs
        for dy in (-1, 1):
            comps = comps.cut(cq.Workplane("XY").workplane(offset=z0).center(dx * b["pitch"] / 2, dy * b["pitch"] / 2)
                              .circle(3.2).extrude(b["comp_h"] + b["pcb_t"] + 1))
    top = z0 + b["pcb_t"] + b["comp_h"]
    r = CONFIG["rx"]["size"]
    rx = cq.Workplane("XY").workplane(offset=top).center(0, -6).rect(r[0], r[1]).extrude(r[2])
    # antenna leaves the RX horizontally to the rear, between the M3/M4 guards and under the cradle (not up through the pack)
    antenna = cq.Workplane("XY").add(cq.Solid.makeCylinder(0.6, 40.0, cq.Vector(0, -6 - r[1] / 2, top + r[2] / 2), cq.Vector(0, -1, 0)))
    return pcb, comps, antenna, rx, top


FOOT_H = 17.5   # MTF-01 is 14.5 mm tall + 3 mm: the aircraft must never land on the sensor


def foot_solid():
    """Landing foot under a guard ear: a cup. An M2 screw goes up from inside the cup (head in the Ø4.4 bore, on a
    2 mm floor) through the plate and the guard foot, nyloc nut on top. Short common screw whatever the foot height."""
    f = cq.Workplane("XY").circle(3.6).extrude(FOOT_H)
    f = f.cut(cq.Workplane("XY").workplane(offset=-1).circle(1.1).extrude(FOOT_H + 2))
    f = f.cut(cq.Workplane("XY").workplane(offset=-0.01).circle(2.2).extrude(FOOT_H - 2.0))
    return f


def standoffs(z_from, z_to, pitch):
    s = None
    for dx in (-1, 1):
        for dy in (-1, 1):
            c = cq.Workplane("XY").workplane(offset=z_from).center(dx * pitch / 2, dy * pitch / 2).circle(2.6).circle(1.6).extrude(z_to - z_from)
            s = c if s is None else s.union(c)
    return s


def pack_solids(z0):
    """z0 = cradle base top. One 12 mm x 1 mm strap ACROSS the pack at mid-length: under the base between the two
    slots, up through them, up the pack sides and over the top. The XT30 end of the pack stays free."""
    L, W, H = CONFIG["pack"]["dims"]
    pack = cq.Workplane("XY").workplane(offset=z0).rect(L, W).extrude(H)
    xt30 = cq.Workplane("XY").workplane(offset=z0 + H / 2 - 2.5).center(L / 2 + 12, 0).rect(10.0, 5.0).extrude(5.0)
    lead = cq.Workplane("XY").workplane(offset=z0 + H / 2 - 1).center(L / 2 + 3.5, 0).rect(7.0, 2.0).extrude(2.0)
    sw, ys = V.STRAP_W, W / 2 + 2.3
    def bx(y0, y1, z_0, z_1):
        return cq.Workplane("XY").workplane(offset=z_0).center(0, (y0 + y1) / 2).rect(sw, abs(y1 - y0)).extrude(z_1 - z_0)
    zb = z0 - V.CRADLE_T - 1.0            # under the cradle base
    strap = (bx(-ys - 0.5, ys + 0.5, zb, zb + 1.0)
             .union(bx(-ys - 0.5, -ys + 0.5, zb, z0 + H + 1.0)).union(bx(ys - 0.5, ys + 0.5, zb, z0 + H + 1.0))
             .union(bx(-ys - 0.5, ys + 0.5, z0 + H, z0 + H + 1.0)))
    return pack, xt30.union(lead), strap


# ------------------------------------------------------------------ mass properties
def mass_props(shape_wp, mass_g=None, rho=None):
    """mass (g), CG (mm), inertia about own CG (g*mm^2, 3x3) for a cadquery solid, from its geometry."""
    from OCP.BRepGProp import BRepGProp
    from OCP.GProp import GProp_GProps
    shp = shape_wp.val() if hasattr(shape_wp, "val") else shape_wp
    if hasattr(shape_wp, "vals") and len(shape_wp.vals()) > 1:
        shp = cq.Compound.makeCompound(shape_wp.vals())
    p = GProp_GProps()
    BRepGProp.VolumeProperties_s(shp.wrapped, p)
    vol = p.Mass()
    m = mass_g if mass_g is not None else vol * rho
    dens = m / vol
    c = p.CentreOfMass()
    M = p.MatrixOfInertia()
    Iu = np.array([[M.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)])
    return m, np.array([c.X(), c.Y(), c.Z()]), Iu * dens


def combine(parts):
    mt = sum(m for m, _, _ in parts)
    cg = sum(m * c for m, c, _ in parts) / mt
    I = np.zeros((3, 3))
    for m, c, Ic in parts:
        d = c - cg
        I += Ic + m * (np.dot(d, d) * np.eye(3) - np.outer(d, d))
    return mt, cg, I


def located(wp, x=0.0, y=0.0, z=0.0, rz=0.0):
    return wp.rotate((0, 0, 0), (0, 0, 1), rz).translate((x, y, z))


# ------------------------------------------------------------------ renders
LIGHT = np.array([0.35, -0.45, 0.82]) / np.linalg.norm([0.35, -0.45, 0.82])


def render(items, path, title, elev=28, azim=-55):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    fig = plt.figure(figsize=(9, 7))
    ax = fig.add_subplot(111, projection="3d")
    allp, polys, cols = [], [], []
    for wp, color in items:
        for sh in (wp.vals() if hasattr(wp, "vals") else [wp]):
            verts, tris = sh.tessellate(0.4, 0.5)
            P = np.array([[v.x, v.y, v.z] for v in verts])
            if len(tris) == 0:
                continue
            T = np.array([P[list(t)] for t in tris])
            n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
            n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
            lum = 0.45 + 0.55 * np.abs(n @ LIGHT)
            fc = np.clip(np.outer(lum, color), 0, 1)
            polys.append(T)
            cols.append(fc)
            allp.append(P)
    # one collection: matplotlib depth-sorts faces only within a collection, so separate parts drew in the wrong order
    ax.add_collection3d(Poly3DCollection(np.vstack(polys), facecolors=np.vstack(cols), edgecolors="none"))
    P = np.vstack(allp)
    lo, hi = P.min(0), P.max(0)
    ax.set_xlim(lo[0], hi[0]); ax.set_ylim(lo[1], hi[1]); ax.set_zlim(lo[2], hi[2])
    ax.set_box_aspect(hi - lo)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(title, fontsize=10)
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def main():
    R, t, w, sizing = size_arm()
    v = variant(R, t, w)
    V.HERE = HERE
    chk = V.build(v)             # print files + checks.json in CHEAP_PrintFiles/

    # ---- assembly
    outline, holes = V.plate_outline(v), V.plate_holes(v)
    plate = V.plate_solid(v, outline, holes).translate((0, 0, -t))
    guard, _, _ = V.guard_solid(v)
    cradle = V.cradle_solid(v)
    pcb, comps, antenna, rx, board_top = board_solids()
    cradle_z = 19.0 + 3.0 - 2.0                       # pack bottom 3 mm above the 19 mm guard tops
    so_low = standoffs(0.0, CONFIG["board"]["standoff_h"], CONFIG["board"]["pitch"])
    so_high = standoffs(CONFIG["board"]["standoff_h"] + CONFIG["board"]["pcb_t"], cradle_z, CONFIG["board"]["pitch"])
    pack, xt30, strap = pack_solids(cradle_z + V.CRADLE_T)   # cradle base top
    mot = motor_solid()
    prop, prop_z = prop_solid()

    C = {"plate": (0.25, 0.25, 0.27), "guard": (0.93, 0.45, 0.10), "motor": (0.62, 0.62, 0.66), "prop": (0.15, 0.62, 0.48),
         "pcb": (0.10, 0.35, 0.65), "comp": (0.12, 0.12, 0.12), "so": (0.85, 0.80, 0.60), "cradle": (0.93, 0.45, 0.10),
         "pack": (0.85, 0.16, 0.50), "xt30": (0.95, 0.80, 0.10), "strap": (0.2, 0.2, 0.2), "ant": (0.1, 0.1, 0.1)}
    E = CONFIG["extra_mass_g"]
    parts = []        # (name, wp, color, mass_g or None, rho or None, explode_dz)
    parts.append(("frame plate (ABS)", plate, C["plate"], None, RHO_ABS, 0))
    for i in range(4):
        x, y, a = V.motor_xy(v, i)
        deg = math.degrees(a)
        parts.append((f"guard {i+1} (ABS)", located(guard, x, y, 0, deg), C["guard"], None, RHO_ABS, 52))
        parts.append((f"motor {i+1}", located(mot, x, y), C["motor"], CONFIG["motor"]["mass_g"], None, 22))
        parts.append((f"prop {i+1}", located(prop, x, y, 0, 15 * i), C["prop"], CONFIG["prop"]["mass_g"], None, 36))
    foot = foot_solid()
    cq.exporters.export(foot, str(HERE / "CHEAP_PrintFiles" / "CHEAP_Landing_Foot_x4.stl"))
    for i in range(4):
        x, y, a = V.motor_xy(v, i)
        ex, ey = x + v.ear_r * math.cos(a + math.pi / 2), y + v.ear_r * math.sin(a + math.pi / 2)
        parts.append((f"landing foot {i+1} (ABS)", foot.translate((ex, ey, -t - FOOT_H)), C["plate"], None, RHO_ABS, -25))
    if CONFIG["flow"]["fitted"]:
        f = CONFIG["flow"]["size"]
        flow = cq.Workplane("XY").workplane(offset=-t - f[2]).center(0, 9.0).rect(f[0], f[1]).extrude(f[2])
        parts.append(("MTF-01 flow/ToF (under plate)", flow, (0.1, 0.1, 0.1), CONFIG["flow"]["mass_g"], None, -15))
    parts += [("AIO standoffs", so_low, C["so"], 0.4, None, 8),
              ("AIO board (FC + ESC + RX)", pcb.union(comps), C["pcb"], CONFIG["board"]["mass_g"], None, 12),
              ("ELRS receiver", rx, C["comp"], CONFIG["rx"]["mass_g"], None, 16),
              ("RX antenna", antenna, C["ant"], 0.3, None, 16),
              ("cradle standoffs", so_high, C["so"], 1.2, None, 64),
              ("battery cradle (ABS)", cradle.translate((0, 0, cradle_z)), C["cradle"], None, RHO_ABS, 74),
              ("pack", pack, C["pack"], CONFIG["pack"]["mass_g"], None, 92),
              ("XT30 + lead", xt30, C["xt30"], E["wiring + XT30 pigtail + cap"], None, 92),
              ("strap", strap, C["strap"], E["strap"], None, 92)]
    # centre the CG on the thrust axis by sliding the pack (and its lead) in the cradle; the strap allows it.
    # Without this the XT30 lead (4.5 g, 40 mm forward) put the CG 1.07 mm forward.
    pre = [mass_props(wp, m, rho) for _, wp, _, m, rho, _ in parts]
    m_all = sum(q[0] for q in pre) + E["screws, nuts, standoffs"]
    cg_pre = sum(q[0] * q[1] for q in pre) / m_all
    movers = ("pack", "XT30 + lead")
    m_move = sum(q[0] for (n, *_), q in zip(parts, pre) if n in movers)
    pack_dx, pack_dy = (round(float(-cg_pre[0] * m_all / m_move), 1), round(float(-cg_pre[1] * m_all / m_move), 1))
    parts = [(n, wp.translate((pack_dx, pack_dy, 0)) if n in movers else wp, c, m, r, dz) for n, wp, c, m, r, dz in parts]
    print(f"pack shifted {pack_dx} mm (x), {pack_dy} mm (y) to centre the CG (was {cg_pre[0]:.2f}, {cg_pre[1]:.2f} mm)")
    asm = cq.Assembly(name="Cheapest_drone")
    exp = cq.Assembly(name="Cheapest_drone_exploded")
    for name, wp, col, _, _, dz in parts:
        asm.add(wp, name=name.replace(" ", "_").replace("(", "").replace(")", "").replace("+", "and"), color=cq.Color(*col))
        exp.add(wp.translate((0, 0, dz)), name=name.replace(" ", "_").replace("(", "").replace(")", "").replace("+", "and"),
                color=cq.Color(*col))
    asm.save(str(HERE / "Cheapest_Assembly.step"))
    exp.save(str(HERE / "Cheapest_Assembly_Exploded.step"))

    # ---- interference check: every pair of parts, bounding-box prefilter, then solid intersection volume
    clashes = []
    shp = [(n, (wp.vals() and cq.Compound.makeCompound(wp.vals())) if hasattr(wp, "vals") else wp) for n, wp, *_ in parts]
    for i in range(len(shp)):
        for j in range(i + 1, len(shp)):
            (na, A), (nb, B) = shp[i], shp[j]
            ba, bb = A.BoundingBox(), B.BoundingBox()
            if ba.xmax < bb.xmin or bb.xmax < ba.xmin or ba.ymax < bb.ymin or bb.ymax < ba.ymin or ba.zmax < bb.zmin or bb.zmax < ba.zmin:
                continue
            vol = A.intersect(B).Volume()
            if vol > 0.05:
                clashes.append({"a": na, "b": nb, "overlap_mm3": round(vol, 2)})
    (HERE / "assembly_interference.json").write_text(json.dumps({"pairs_checked": len(shp) * (len(shp) - 1) // 2,
                                                                 "clashes": clashes}, indent=1))
    print("interference clashes:", clashes)

    # ---- physical model from the CAD
    rows, mp = [], []
    for name, wp, _, mass, rho, _ in parts:
        m, c, I = mass_props(wp, mass, rho)
        mp.append((m, c, I))
        rows.append({"part": name, "mass_g": round(m, 2), "cg_mm": [round(float(q), 2) for q in c],
                     "source": "CAD volume x density" if mass is None else "vendor / estimate"})
    m_screws = E["screws, nuts, standoffs"]
    mp.append((m_screws, np.array([0.0, 0.0, 0.0]), np.zeros((3, 3))))   # spread over the plate: put at the centre
    rows.append({"part": "screws/nuts (lumped at centre)", "mass_g": m_screws, "cg_mm": [0, 0, 0], "source": "estimate"})
    mt, cg, I = combine(mp)
    Ikg = I * 1e-9            # g*mm^2 -> kg*m^2
    full = full_thrust_g()
    tw_full = 4 * full * 0.85 / mt                    # vendor full thrust (7.9 V) with the 0.85 guard retention
    phys = {"total_mass_g": round(mt, 1), "cg_mm": [round(float(q), 2) for q in cg],
            "cg_offset_xy_mm": round(float(math.hypot(cg[0], cg[1])), 2),
            "pack_offset_in_cradle_mm": [pack_dx, pack_dy],
            "inertia_kgm2_about_cg": [[float(f"{q:.4e}") for q in r] for r in Ikg],
            "Ixx_Iyy_Izz_kgm2": [float(f"{Ikg[k, k]:.4e}") for k in range(3)],
            "full_thrust_per_motor_g_vendor": full, "TW_full_pack_with_guards": round(tw_full, 2),
            "motor_diagonal_mm": round(2 * R, 1), "plate_t_mm": t, "arm_w_mm": w, "arm_sizing": sizing,
            "parts": rows, "config": CONFIG}
    (HERE / "physical_model.json").write_text(json.dumps(phys, indent=1))

    # ---- SITL frame model from the physical model (same fields as make_revs_models.py)
    rot = [r for r in rows if r["part"].startswith("motor")]
    hover_a_est = None
    try:
        sys.path.insert(0, str(HERE.parent.parent / "00_System_Integration" / "Analysis" / "evolve"))
        import evolve_drone as EV
        cat = EV.load_catalog(str(V.CATALOG))
        pair = next(p for p in cat["pairs"] if cat["motors"][p["motor"]]["name"] == CONFIG["motor"]["name"] and p["prop"] == CONFIG["prop"]["name"])
        hover_a_est = 4 * EV.interp_current(pair["rows"], mt / 4 / 0.85, 7.4)
    except Exception as e:   # fall back to a planning number
        print("hover current estimate failed:", e)
    v_full = 8.7
    disc = math.pi * (CONFIG["prop"]["d"] / 2000) ** 2 * 4
    sitl = {"mass": round(mt / 1000, 4), "diagonal_size": round(R / 1000, 4), "refSpd": 8.0, "refAngle": 25.0,
            "refVoltage": 7.4, "refCurrent": round(hover_a_est or 8.0, 2), "refAlt": 10, "refTempC": 20, "refBatRes": 0.029,
            "maxVoltage": v_full, "battCapacityAh": 2.0, "propExpo": 0.55, "refRotRate": 360,
            "hoverThrOut": round(1.0 / (tw_full * (v_full / 7.9) ** 2), 3), "pwmMin": 1000, "pwmMax": 2000,
            "spin_min": 0.10, "spin_max": 0.95, "slew_max": 30, "disc_area": round(disc, 5), "mdrag_coef": 0.2,
            "moment_inertia": [float(f"{Ikg[0, 0]:.3e}"), float(f"{Ikg[1, 1]:.3e}"), float(f"{Ikg[2, 2]:.3e}")],
            "num_motors": 4}
    (HERE / "sitl_cheapest.json").write_text(json.dumps(sitl, indent=1))

    # ---- renders
    items = [(wp, col) for _, wp, col, *_ in parts]
    render(items, HERE / "render_assembly_iso.png", f"Cheapest drone, assembled ({mt:.0f} g, {2*R:.0f} mm diagonal)")
    render([(wp.translate((0, 0, dz)), col) for _, wp, col, _, _, dz in parts], HERE / "render_exploded.png",
           "Exploded (bottom to top): feet, flow sensor, plate, AIO + RX, motors, props, guards, cradle, pack", elev=18)
    render(items, HERE / "render_side.png", "Side view", elev=0, azim=-90)
    render(items, HERE / "render_top.png", "Top view", elev=90, azim=-90)
    print(json.dumps({k: phys[k] for k in phys if k not in ("parts", "config")}, indent=1))
    print("print-file checks:", {k: chk[k] for k in ("plate_mass_g", "guard_mass_g_each", "arm_flap_mode_Hz",
                                                     "arm_torsion_mode_Hz", "guard_to_esc_board_gap_mm",
                                                     "pack_corner_to_guard_plan_gap_mm", "plate_valid_solid", "guard_valid_solid")})


if __name__ == "__main__":
    main()
