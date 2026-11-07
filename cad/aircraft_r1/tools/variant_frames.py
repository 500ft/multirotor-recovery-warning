"""Frame, guard, cradle and jig files for the three evolved variants (B, C, D).

Same geometry method as ../RevS/revs_frame.py and revs_makerspace.py, with each variant's parts taken from
00_System_Integration/Analysis/evolve (Pareto designs) and catalog.json:

  B_Cheapest_Paper   $242  Matek H743-MINI V3 + SEQURE Blueson A1 65A AM32 + BetaFPV 1103 / GF 2218-3 + CNHL 650 2S
                           printed CF-PETG plate 4 mm, 124.6 mm diagonal, 8.7 mm arms, TPU rings
  C_Maxed_Out        $326  Matek + Aikon AK32PIN 35A + RCinPower GTS V2 1202.5 11500KV / GF 65R + BETAFPV LAVA 450 2S
                           2 mm carbon plate, 128.9 mm diagonal, 6.8 mm arms, TPU ducts
  D_Cheapest_Flyer   $148  HappyModel CrazyF405HD 1-2S AIO (25.5 M2) + BetaFPV 1103 / GF 2218-3 + CNHL 650 2S
                           printed CF-PETG plate 4 mm, 114.3 mm diagonal, 6.1 mm arms, TPU rings (not paper-grade)

Per variant folder: plate DXF (+ waterjet DXF for carbon), plate STEP/STL, guard STEP/STL, battery cradle STL,
motor-pad drill jig STL where RevS's jig does not fit, preview PNG, checks.json.

Run: python variant_frames.py   (needs cadquery, shapely, ezdxf, matplotlib)
"""
import json
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path

import cadquery as cq
import ezdxf
from shapely import affinity
from shapely.geometry import Point, box
from shapely.ops import unary_union

HERE = Path(__file__).parent
CATALOG = HERE.parent.parent / "00_System_Integration" / "Analysis" / "evolve" / "catalog.json"
G0 = 9.80665
RHO_TPU = 1.21e-3          # g/mm^3 TPU 92A
RHO_GUARD = {"TPU": 1.21e-3, "ABS": 1.04e-3}
MIN_WATERJET_HOLE = 3.2    # SendCutSend / waterjet minimum hole (same rule as RevS)
JIG_T, GUIDE_CLR = 6.0, 0.15

MATERIALS = {
    # E, G in N/mm^2 (in-plane), rho g/mm^3
    "cf_plate": {"E": 45e3, "G": 17e3, "rho": 1.55e-3, "label": "3K carbon plate (quasi-iso)",
                 "process": "waterjet / CNC (Tandon WardJet or SendCutSend)"},
    # ABS (Stratasys ABS-M30 / ABSplus, enclosed printer), flat, solid fill: planning values, ASSUMPTION
    # (vendor tensile modulus 2.2-2.4 GPa; 2.0 used for printed in-plane bending)
    "abs_print": {"E": 2.0e3, "G": 0.75e3, "rho": 1.04e-3, "label": "ABS FDM (Stratasys F170/F370), printed flat, solid",
                  "process": "FDM ABS at the makerspace (Stratasys, enclosed)"},
    # CF-PETG flat-printed, in-plane values for ~100 % infill: planning numbers, ASSUMPTION (E 3.5-4.5 GPa)
    "petg_cf_print": {"E": 3.8e3, "G": 1.4e3, "rho": 1.30e-3, "label": "CF-PETG FDM, printed flat",
                      "process": "FDM CF-PETG at the makerspace (hardened nozzle)"},
}


@dataclass
class Variant:
    key: str
    title: str
    cost_usd: float
    pareto_ref: str
    material: str
    plate_t: float
    motor_r: float                 # centre to motor axis (half the diagonal)
    arm_w: float
    core: float
    fillet: float                  # inside-corner fillet; printed frames get big root fillets (Goblin lesson)
    stack_pitch: float
    stack_hole: float
    stack_label: str
    motor: str
    prop: str
    prop_d: float
    motor_pcd: float
    motor_holes: int
    motor_hole_d: float
    motor_hole_label: str
    shaft_clr: float
    pad_d: float
    ear_r: float
    bell_d: float
    guard_kind: str                # "ring" or "duct"
    guard_h: float
    esc_board: tuple
    fc_board: tuple
    pack_name: str
    pack: tuple                    # L, W, H mm
    reuse_revs_jig: bool
    notes: list = field(default_factory=list)
    guard_material: str = "TPU"     # "TPU" (92A) or "ABS"
    guard_wall: float = 2.0
    alt_ring: bool = False         # also generate a plain TPU ring (C: start with rings, ducts are the later experiment)


EAR_W, GUARD_WALL, FOOT_T, PROP_CLR = 6.0, 2.0, 2.6, 2.5

VARIANTS = [
    Variant(
        key="B_Cheapest_Paper", title="B - cheapest paper-grade", cost_usd=241.69, pareto_ref="pareto_paper row 1",
        material="petg_cf_print", plate_t=6.0, motor_r=62.3, arm_w=9.0, core=36.0, fillet=4.0,
        stack_pitch=20.0, stack_hole=3.2, stack_label="stack M3 20x20",
        motor="BetaFPV 1103 10500KV", prop="GF 2218-3", prop_d=2.2 * 25.4,
        motor_pcd=6.6, motor_holes=3, motor_hole_d=1.6, motor_hole_label="M1.4", shaft_clr=3.5,
        pad_d=17.0, ear_r=9.5, bell_d=13.5, guard_kind="ring", guard_h=19.0,
        esc_board=(42.5, 36.0), fc_board=(36.0, 28.0),
        pack_name="CNHL MiniStar 2S 650 70C", pack=(58.0, 30.0, 15.0), reuse_revs_jig=False,
        notes=["SEQURE Blueson A1 8-pin order not verified against the Matek: check with a meter before plugging in, re-pin cable if needed (T8)",
               "printed arm is the stiffness-limited part: run the arm tilt and tap/mode tests (T3, T4) on the first print before fitting electronics"]),
    Variant(
        key="C_Maxed_Out", title="C - maxed-out (highest ballast range)", cost_usd=325.88, pareto_ref="pareto_paper row 59 (SITL row 65 run)",
        material="cf_plate", plate_t=3.0, motor_r=64.45, arm_w=10.0, core=36.0, fillet=1.0,
        stack_pitch=20.0, stack_hole=3.2, stack_label="stack M3 20x20",
        motor="RCinPower GTS V2 1202.5 11500KV", prop="GF 65R", prop_d=65.0,
        motor_pcd=9.0, motor_holes=4, motor_hole_d=2.2, motor_hole_label="M2", shaft_clr=3.5,
        pad_d=19.0, ear_r=11.0, bell_d=15.5, guard_kind="duct", guard_h=20.0,
        esc_board=(36.0, 36.0), fc_board=(36.0, 28.0),
        pack_name="BETAFPV LAVA 2S 450 75C", pack=(63.0, 15.5, 13.5), reuse_revs_jig=False, alt_ring=True,
        notes=["motor pattern 4x M2 on a 9 mm circle and 1.5 mm prop shaft from retailer listings (Rotorama, GetFPV): measure the delivered motor before drilling (T1)",
               "bell diameter 15.5 mm is an ASSUMPTION for the guard foot: measure and re-run if the bell is larger than 16.5 mm",
               "Aikon AK32PIN board outline not published (36x36 assumed): measure; 8-pin order not verified against the Matek (T8)",
               "start rate gains at x0.5 of RevS (SITL: 0.03 P/I, 0.00075 D) and AutoTune before trials (T12)"]),
    Variant(
        key="D_Cheapest_Flyer", title="D - cheapest flyer (no Lua, not paper-grade)", cost_usd=147.56, pareto_ref="pareto_cheapest_flyer row 1",
        material="petg_cf_print", plate_t=5.0, motor_r=57.15, arm_w=10.5, core=34.0, fillet=4.0,
        stack_pitch=25.5, stack_hole=2.2, stack_label="AIO M2 25.5x25.5",
        motor="BetaFPV 1103 10500KV", prop="GF 2218-3", prop_d=2.2 * 25.4,
        motor_pcd=6.6, motor_holes=3, motor_hole_d=1.6, motor_hole_label="M1.4", shaft_clr=3.5,
        pad_d=17.0, ear_r=9.5, bell_d=13.5, guard_kind="ring", guard_h=19.0,
        esc_board=(32.0, 32.0), fc_board=(32.0, 32.0),
        pack_name="CNHL MiniStar 2S 650 70C", pack=(58.0, 30.0, 15.0), reuse_revs_jig=False,
        notes=["CrazyF405HD board outline taken as 32x32 (whoop AIO): measure",
               "F405: no Lua and no bidirectional DShot in ArduPilot: drop_trigger.lua cannot run, so this is a pilot-training / second platform only"]),
]


# ------------------------------------------------------------------ catalogue data
def catalog_parts(v):
    cat = json.load(open(CATALOG, encoding="utf-8"))
    motor = next(m for m in cat["motors"] if m["name"] == v.motor)
    prop = next(p for p in cat["props"] if p["name"] == v.prop)
    rows = [r for r in motor["thrust_table"] if r["prop"] == v.prop]
    full = max(rows, key=lambda r: r["thrust_g"])
    return motor, prop, full


# ------------------------------------------------------------------ geometry
def motor_xy(v, i):
    a = math.radians(45 + 90 * i)
    return v.motor_r * math.cos(a), v.motor_r * math.sin(a), a


def plate_outline(v):
    core = box(-v.core / 2, -v.core / 2, v.core / 2, v.core / 2).buffer(-3.0).buffer(3.0)
    parts = [core]
    for i in range(4):
        x, y, a = motor_xy(v, i)
        parts.append(affinity.rotate(box(0, -v.arm_w / 2, v.motor_r, v.arm_w / 2), a, origin=(0, 0), use_radians=True))
        parts.append(Point(x, y).buffer(v.pad_d / 2, 64))
        ear = box(-EAR_W / 2, -v.ear_r - 3.2, EAR_W / 2, v.ear_r + 3.2).buffer(0.8)
        parts.append(affinity.translate(affinity.rotate(ear, a, origin=(0, 0), use_radians=True), x, y))
    return unary_union(parts).buffer(v.fillet).buffer(-v.fillet)


def plate_holes(v):
    holes = []
    for i in range(4):
        x, y, a = motor_xy(v, i)
        holes.append((x, y, v.shaft_clr, f"M{i+1} shaft/circlip"))
        for k in range(v.motor_holes):
            b = a + 2 * math.pi * k / v.motor_holes
            holes.append((x + v.motor_pcd / 2 * math.cos(b), y + v.motor_pcd / 2 * math.sin(b), v.motor_hole_d,
                          f"M{i+1} {v.motor_hole_label}"))
        for s in (-1, 1):
            b = a + s * math.pi / 2
            holes.append((x + v.ear_r * math.cos(b), y + v.ear_r * math.sin(b), 2.2, f"M{i+1} guard M2"))
    for sx in (-1, 1):
        for sy in (-1, 1):
            holes.append((sx * v.stack_pitch / 2, sy * v.stack_pitch / 2, v.stack_hole, v.stack_label))
    holes.append((0.0, 0.0, 3.2, "ballast post M3 (thrust axis)"))
    for sx in (-1, 1):
        holes.append((sx * 13.0, 0.0, 3.2, "offset ballast M3"))
    holes.append((0.0, 14.5, 2.2, "MTF-01 / zip tie front"))
    holes.append((0.0, -14.5, 2.2, "RX antenna / zip tie rear"))
    return holes


def write_dxf(v, outline, holes, path, min_hole=0.0):
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.layers.add("CUT", color=1)
    doc.layers.add("NOTES", color=3)
    msp = doc.modelspace()
    msp.add_lwpolyline(list(outline.exterior.coords), close=True, dxfattribs={"layer": "CUT"})
    drilled = []
    for x, y, d, use in holes:
        if d >= min_hole:
            msp.add_circle((x, y), d / 2, dxfattribs={"layer": "CUT"})
        else:
            drilled.append((round(x, 3), round(y, 3), d, use))
    note = (f"{v.title} plate - {v.plate_t} mm {MATERIALS[v.material]['label']} - mm - outline + holes on layer CUT"
            + (f" - holes < {min_hole} mm omitted: drill with the printed jig" if min_hole else ""))
    msp.add_text(note, height=1.5, dxfattribs={"layer": "NOTES"}).set_placement((-v.motor_r, -v.motor_r - 12))
    doc.saveas(path)
    return drilled


def plate_solid(v, outline, holes):
    pts = list(outline.exterior.coords)[:-1]
    s = cq.Workplane("XY").polyline(pts).close().extrude(v.plate_t)
    for x, y, d, _ in holes:
        s = s.cut(cq.Workplane("XY").workplane(offset=-1).center(x, y).circle(d / 2).extrude(v.plate_t + 2))
    # thick printed plates: counterbore the M1.4 motor-screw holes from below (Ø3.0, leaves 3 mm) so the common
    # M1.4 x 5 screw still reaches the motor; M1.4 screws long enough for a 5-7 mm plate are hard to buy
    if v.material != "cf_plate" and v.plate_t > 3.5:
        for x, y, d, use in holes:
            if d < 2.0 and "M1.4" in use:
                s = s.cut(cq.Workplane("XY").workplane(offset=-1).center(x, y).circle(1.5).extrude(v.plate_t - 3.0 + 1))
    return s


def guard_solid(v):
    """FDM TPU guard, local frame: motor axis at origin, arm along -x, bolt ears on +-y (same layout as RevS)."""
    ri = v.prop_d / 2 + PROP_CLR
    foot_id, foot_od = v.bell_d + 1.5, v.bell_d + 9.5
    if v.guard_kind == "ring":
        wall = cq.Workplane("XY").circle(ri + v.guard_wall).circle(ri).extrude(v.guard_h)
        r_top = ri + v.guard_wall
    else:
        # duct: straight wall with a bell-mouth inlet lip (radius RL) on top; lip is the only part wider than the ring
        RL, H, w = max(4.0, v.guard_wall + 2.0), v.guard_h, v.guard_wall
        n = 12
        prof = [(ri, 0.0), (ri + w, 0.0), (ri + w, H - RL)]
        for k in range(1, n + 1):  # outer surface of the lip, radius RL - w about (ri + RL, H - RL)
            t = math.pi - (math.pi / 2) * k / n
            prof.append((ri + RL + (RL - w) * math.cos(t), H - RL + (RL - w) * math.sin(t)))
        for k in range(n):         # flow surface, radius RL, from the top back down to the straight wall
            t = math.pi / 2 + (math.pi / 2) * k / n
            prof.append((ri + RL + RL * math.cos(t), H - RL + RL * math.sin(t)))
        wall = cq.Workplane("XZ").polyline(prof).close().revolve(360, (0, 0, 0), (0, 1, 0))
        r_top = ri + RL
    foot = cq.Workplane("XY").circle(foot_od / 2).circle(foot_id / 2).extrude(FOOT_T)
    r0, r1 = foot_od / 2 - 0.5, ri + 0.5
    spokes = (cq.Workplane("XY").center(0, (r0 + r1) / 2).rect(4.0, r1 - r0).extrude(FOOT_T)
              .union(cq.Workplane("XY").center(0, -(r0 + r1) / 2).rect(4.0, r1 - r0).extrude(FOOT_T)))
    ears = (cq.Workplane("XY").center(0, v.ear_r).circle(3.0).extrude(FOOT_T)
            .union(cq.Workplane("XY").center(0, -v.ear_r).circle(3.0).extrude(FOOT_T)))
    g = wall.union(foot).union(spokes).union(ears)
    for s in (-1, 1):
        g = g.cut(cq.Workplane("XY").workplane(offset=-1).center(0, s * v.ear_r).circle(1.1).extrude(FOOT_T + 2))
    # keep the motor bell's space clear: the ear bosses (r 3 at ear_r) reached 0.25 mm inside a 13.5 mm bell
    # (found by the assembly interference check, 2026-11-06)
    g = g.cut(cq.Workplane("XY").workplane(offset=-1).circle(foot_id / 2).extrude(FOOT_T + 2))
    return g, ri + v.guard_wall, r_top


STRAP_W = 12.0     # strap width (x); one strap across the pack width at mid-length
CRADLE_T = 3.0     # base: 3 mm so the M3 button heads (1.65 mm) sit flush in 2.0 mm counterbores under the pack


def cradle_solid(v):
    """Battery cradle on the stack holes. One strap goes ACROSS the pack (y) at mid-length through two 14 x 3 mm slots
    just outside the pack sides. The first cradle looped the strap along the pack length through slots under the pack,
    which wraps the strap over the end where the XT30 lead leaves the pack (found by the assembly interference check)."""
    L, W, H = v.pack
    half_l = max(30.0, L / 2 - 2.0)
    # room for the strap slot (1.2 mm outer web) AND >= 4 mm of base around each stack hole (a narrow pack on a 20 mm
    # stack left only 1.15 mm, found 2026-11-07)
    half_w = max(W / 2 + 5.0, v.stack_pitch / 2 + 4.0)
    s = cq.Workplane("XY").rect(2 * half_l, 2 * half_w).extrude(CRADLE_T)
    gap = STRAP_W / 2 + 2.0                   # side walls stop where the strap passes
    for sy in (-1, 1):
        for sx in (-1, 1):
            x0, x1 = sx * gap, sx * half_l
            s = s.union(cq.Workplane("XY").workplane(offset=CRADLE_T)
                        .center((x0 + x1) / 2, sy * (W / 2 + 0.3 + (half_w - W / 2 - 0.3) / 2))
                        .rect(abs(x1 - x0), half_w - W / 2 - 0.3).extrude(6.0))
        s = s.cut(cq.Workplane("XY").workplane(offset=-1).center(0, sy * (W / 2 + 2.3)).rect(STRAP_W + 2.0, 3.0).extrude(CRADLE_T + 2))
    for sx in (-1, 1):
        for sy in (-1, 1):
            s = s.cut(cq.Workplane("XY").workplane(offset=-1).center(sx * v.stack_pitch / 2, sy * v.stack_pitch / 2)
                      .circle(v.stack_hole / 2).extrude(10.0))
            # counterbore 1.8 mm into the base and clear through any wall above, so an M3 button head (1.65 mm) sits
            # flush under the pack and never lands on a wall top (found 2026-11-06/07)
            s = s.cut(cq.Workplane("XY").workplane(offset=CRADLE_T - 1.8).center(sx * v.stack_pitch / 2, sy * v.stack_pitch / 2)
                      .circle(3.3).extrude(10.0))
    return s


def motor_pad_jig(v):
    """Drill guide for the small holes on one motor pad (RevS revs_makerspace.motor_pad_jig, re-parameterised)."""
    body = cq.Workplane("XY").circle(v.pad_d / 2 + 3.0).extrude(JIG_T)
    jig = body.union(cq.Workplane("XY").rect(EAR_W + 6.0, 2 * (v.ear_r + 4.0)).extrude(JIG_T))
    jig = (jig.cut(cq.Workplane("XY").circle(v.pad_d / 2 + 0.2).extrude(1.5))
              .cut(cq.Workplane("XY").rect(EAR_W + 2.0, 2 * (v.ear_r + 3.2) + 2.0).extrude(1.5))
              # the arm must sit in the pocket too, or the jig rests flat on the arm and can rotate about the pin
              .cut(cq.Workplane("XY").center(-(v.pad_d / 2 + 4.0) / 2, 0).rect(v.pad_d / 2 + 4.0, v.arm_w + 0.4).extrude(1.5)))
    jig = jig.union(cq.Workplane("XY").workplane(offset=-3.0).circle((v.shaft_clr - 0.1) / 2).extrude(4.5))
    for k in range(v.motor_holes):
        b = 2 * math.pi * k / v.motor_holes
        jig = jig.cut(cq.Workplane("XY").workplane(offset=-4).center(v.motor_pcd / 2 * math.cos(b), v.motor_pcd / 2 * math.sin(b))
                      .circle((v.motor_hole_d + GUIDE_CLR) / 2).extrude(JIG_T + 8))
    for s in (-1, 1):
        jig = jig.cut(cq.Workplane("XY").workplane(offset=-4).center(0, s * v.ear_r).circle((2.2 + GUIDE_CLR) / 2).extrude(JIG_T + 8))
    return jig


# ------------------------------------------------------------------ checks
def board_gap(v, r_out, board):
    bx, by = board[0] / 2, board[1] / 2
    gaps = []
    for i in range(4):
        x, y, _ = motor_xy(v, i)
        gaps.append(math.hypot(max(abs(x) - bx, 0), max(abs(y) - by, 0)) - r_out)
    return min(gaps)


def checks(v, outline, holes, guard, r_ring, r_top, cradle):
    motor, prop, full = catalog_parts(v)
    mat = MATERIALS[v.material]
    plate = outline
    for x, y, d, _ in holes:
        plate = plate.difference(Point(x, y).buffer(d / 2, 32))
    out = {"variant": v.title, "pareto_ref": v.pareto_ref, "material": mat["label"], "plate_t_mm": v.plate_t,
           "diagonal_mm": round(2 * v.motor_r, 1), "arm_w_mm": v.arm_w}
    out["plate_mass_g"] = round(plate.area * v.plate_t * mat["rho"], 2)
    g_vol = guard.val().Volume()
    out["guard_kind"] = v.guard_kind
    out["guard_material"] = v.guard_material
    out["guard_mass_g_each"] = round(g_vol * RHO_GUARD[v.guard_material], 2)
    out["guard_valid_solid"] = bool(guard.val().isValid())
    out["cradle_mass_g_TPU_or_PETG"] = round(cradle.val().Volume() * 1.25e-3, 2)
    # arm cantilever from the core edge along the diagonal (same method as revs_frame.checks)
    F = full["thrust_g"] * G0 / 1000.0
    l_free = v.motor_r - (v.core / 2) * math.sqrt(2) + 3.0
    I = v.arm_w * v.plate_t ** 3 / 12
    k_flap = 3 * mat["E"] * I / l_free ** 3
    theta = F * l_free ** 2 / (2 * mat["E"] * I)
    m_tip = motor["mass_g"] + prop["mass_g"] + out["guard_mass_g_each"] + 0.5
    f_flap = math.sqrt(k_flap * 1e3 / (m_tip * 1e-3)) / (2 * math.pi)
    J = v.arm_w * v.plate_t ** 3 / 3 * (1 - 0.63 * v.plate_t / v.arm_w)
    k_t = mat["G"] * J / l_free
    I_tip = (out["guard_mass_g_each"] * 1e-3) * ((r_ring - v.guard_wall / 2) * 1e-3) ** 2 / 2 \
        + (motor["mass_g"] * 1e-3) * ((v.bell_d / 2) * 1e-3) ** 2 / 2
    f_t = math.sqrt(k_t * 1e-3 / I_tip) / (2 * math.pi)
    out["full_thrust_g_vendor"] = full["thrust_g"]
    out["arm_free_length_mm"] = round(l_free, 1)
    out["arm_tilt_deg_at_full_thrust"] = round(math.degrees(theta), 3)
    out["arm_flap_mode_Hz"] = round(f_flap)
    out["arm_torsion_mode_Hz"] = round(f_t)
    out["mode_target_gt_150Hz"] = bool(min(f_flap, f_t) > 150)
    out["tilt_target_lt_1deg"] = bool(math.degrees(theta) < 1.0)
    # clearances
    out["prop_radial_clearance_mm"] = PROP_CLR
    adj = 2 * v.motor_r * math.sin(math.pi / 4)
    out["guard_to_guard_gap_mm"] = round(adj - 2 * r_top, 2)
    out["guard_to_esc_board_gap_mm"] = round(board_gap(v, r_ring, v.esc_board), 2)
    out["guard_top_to_fc_board_gap_mm"] = round(board_gap(v, r_top, v.fc_board), 2)
    mc = (v.motor_r / math.sqrt(2),) * 2
    corner = math.dist((v.pack[0] / 2, v.pack[1] / 2), mc) - r_top
    out["pack"] = f"{v.pack_name} {v.pack[0]}x{v.pack[1]}x{v.pack[2]} mm"
    out["pack_corner_to_guard_plan_gap_mm"] = round(corner, 2)
    out["pack_must_sit_above_guard_tops"] = bool(corner < 3.0)
    out["min_pack_bottom_z_above_plate_mm"] = v.guard_h + 3.0 if corner < 3.0 else None
    # stack/AIO holes must not break into the core edge, motor holes must stay inside the pad
    out["stack_hole_edge_margin_mm"] = round(v.core / 2 - v.stack_pitch / 2 - v.stack_hole / 2, 2)
    out["motor_hole_pad_margin_mm"] = round(v.pad_d / 2 - v.motor_pcd / 2 - v.motor_hole_d / 2, 2)
    out["ear_hole_vs_guard_foot_id_mm"] = round(v.ear_r - 1.1 - (v.bell_d + 1.5) / 2, 2)
    c = plate.centroid
    out["plate_centroid_xy_mm"] = [round(c.x, 3), round(c.y, 3)]
    if v.material == "cf_plate":
        out["min_web_rule_2t_mm"] = 2 * v.plate_t
        out["arm_meets_min_web"] = v.arm_w >= 2 * v.plate_t
    return out


def preview(v, outline, holes, r_ring, r_top, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 7))
    xs, ys = outline.exterior.xy
    ax.fill(xs, ys, color="#333", alpha=0.85, label=f"{v.plate_t} mm {v.material}")
    for x, y, d, _ in holes:
        ax.add_patch(plt.Circle((x, y), d / 2, color="white"))
    for i in range(4):
        x, y, _ = motor_xy(v, i)
        ax.add_patch(plt.Circle((x, y), r_ring, fill=False, color="#d95f02", lw=1.0))
        if r_top > r_ring:
            ax.add_patch(plt.Circle((x, y), r_top, fill=False, color="#d95f02", lw=0.6, ls=":"))
        ax.add_patch(plt.Circle((x, y), v.prop_d / 2, fill=False, ls="--", color="#1b9e77", lw=0.8))
        ax.add_patch(plt.Circle((x, y), v.bell_d / 2, color="#999"))
        ax.text(x, y, f"M{i+1}", ha="center", va="center", fontsize=7)
    ax.add_patch(plt.Rectangle((-v.esc_board[0] / 2, -v.esc_board[1] / 2), *v.esc_board, fill=False, color="#7570b3", label=f"ESC/AIO {v.esc_board[0]}x{v.esc_board[1]}"))
    ax.add_patch(plt.Rectangle((-v.pack[0] / 2, -v.pack[1] / 2), v.pack[0], v.pack[1], fill=False, color="#e7298a", ls=":", label="pack (on cradle)"))
    lim = v.motor_r + v.prop_d / 2 + 12
    ax.set_aspect("equal"); ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
    ax.set_title(f"{v.title} - top view (mm); orange: {v.guard_kind}s, green: props")
    ax.legend(loc="lower left", fontsize=7); ax.grid(alpha=0.2)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def build(v):
    out_dir = HERE / v.key
    out_dir.mkdir(exist_ok=True)
    tag = v.key.split("_")[0]
    outline, holes = plate_outline(v), plate_holes(v)
    stem = f"{tag}_Frame_Plate_{str(v.plate_t).rstrip('0').rstrip('.')}mm"
    write_dxf(v, outline, holes, out_dir / f"{stem}.dxf")
    files = [f"{stem}.dxf"]
    drilled = []
    if v.material == "cf_plate":
        drilled = write_dxf(v, outline, holes, out_dir / f"{stem}_WATERJET_min3p2.dxf", MIN_WATERJET_HOLE)
        files.append(f"{stem}_WATERJET_min3p2.dxf")
    ps = plate_solid(v, outline, holes)
    cq.exporters.export(ps, str(out_dir / f"{stem}.step")); files.append(f"{stem}.step")
    if v.material != "cf_plate":
        cq.exporters.export(ps, str(out_dir / f"{stem}_PRINT.stl"), tolerance=0.02, angularTolerance=0.1)
        files.append(f"{stem}_PRINT.stl")
    g, r_ring, r_top = guard_solid(v)
    gname = f"{tag}_Guard_{'Duct' if v.guard_kind == 'duct' else 'Ring'}_FDM_{v.guard_material}"
    cq.exporters.export(g, str(out_dir / f"{gname}_x4.stl"), tolerance=0.02, angularTolerance=0.1)
    cq.exporters.export(g, str(out_dir / f"{gname}.step"))
    files += [f"{gname}_x4.stl", f"{gname}.step"]
    alt = None
    if v.alt_ring:
        from dataclasses import replace
        ga, _, _ = guard_solid(replace(v, guard_kind="ring", guard_h=19.0))
        an = f"{tag}_Guard_Ring_FDM_{v.guard_material}"
        cq.exporters.export(ga, str(out_dir / f"{an}_x4.stl"), tolerance=0.02, angularTolerance=0.1)
        cq.exporters.export(ga, str(out_dir / f"{an}.step"))
        files += [f"{an}_x4.stl", f"{an}.step"]
        alt = {"kind": "ring", "mass_g_each": round(ga.val().Volume() * RHO_GUARD[v.guard_material], 2), "valid": bool(ga.val().isValid()),
               "note": "start with these; the duct is the later experiment. Modes/clearances above use the heavier, wider duct"}
    cr = cradle_solid(v)
    cq.exporters.export(cr, str(out_dir / f"{tag}_Battery_Cradle.stl")); files.append(f"{tag}_Battery_Cradle.stl")
    jig_valid = None
    if not v.reuse_revs_jig:
        j = motor_pad_jig(v)
        jn = f"{tag}_Drill_Jig_MotorPad_PCD{str(v.motor_pcd).replace('.', 'p')}_{v.motor_holes}hole.stl"
        cq.exporters.export(j, str(out_dir / jn)); files.append(jn)
        jig_valid = bool(j.val().isValid())
    res = checks(v, outline, holes, g, r_ring, r_top, cr)
    res["plate_valid_solid"] = bool(ps.val().isValid())
    if alt:
        res["alt_guard"] = alt
    res["motor_jig"] = (f"generated ({'valid' if jig_valid else 'CHECK'})" if not v.reuse_revs_jig
                        else "reuse ../RevS/manufacturing/RevS_Drill_Jig_MotorPad_PCD6p6_3hole.stl (same pad, ear and hole pattern)")
    res["stack_jig"] = ("reuse ../RevS/manufacturing/RevS_Drill_Jig_Stack_x1.stl (same core hole layout)"
                        if v.stack_pitch == 20.0 else "not needed: all core holes printed")
    res["holes_to_drill_after_waterjet"] = len(drilled)
    res["drill_list"] = drilled
    res["notes"] = v.notes
    res["files"] = files
    res["parameters"] = {k: val for k, val in asdict(v).items() if k not in ("notes",)}
    res["holes"] = [{"x": round(x, 3), "y": round(y, 3), "d": d, "use": u} for x, y, d, u in holes]
    preview(v, outline, holes, r_ring, r_top, out_dir / f"{tag}_preview.png")
    files.append(f"{tag}_preview.png")
    (out_dir / "checks.json").write_text(json.dumps(res, indent=1))
    return res


def main():
    summary = {}
    for v in VARIANTS:
        r = build(v)
        summary[v.key] = {k: r[k] for k in r if k not in ("holes", "parameters", "drill_list", "files", "notes")}
        print(f"\n== {v.title}")
        for k, val in summary[v.key].items():
            print(f"  {k}: {val}")
    (HERE / "variants_summary.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
