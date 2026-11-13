#!/usr/bin/env python
"""
Batch-reactor simulation of an RMG-generated Cantera mechanism (gas phase).

Tested with Cantera 3.2 on RMG-Py 3.3.0 output (examples/rmg/superminimal).

Examples
--------
# list the species names in the mechanism (RMG adds index suffixes like 'H2(1)')
python cantera_batch.py RUN_DIR/cantera/chem_annotated.yaml --list-species

# adiabatic constant-volume ignition at 1000 K, 1 bar, 1 s
python cantera_batch.py RUN_DIR/cantera/chem_annotated.yaml \
    -T 1000 -P 1e5 -X "H2(1):0.67,O2(2):0.33" --t-end 1.0 --out sim

# tolerance-convergence scan of the ignition delay
python cantera_batch.py RUN_DIR/cantera/chem_annotated.yaml \
    -T 1000 -P 1e5 -X "H2(1):0.67,O2(2):0.33" --t-end 1.0 --scan-rtol

Composition keys may be the exact Cantera names ('H2(1)') or the bare RMG
label without the '(n)' suffix ('H2'); bare labels are resolved only if they
are unambiguous.
"""
import argparse
import re
import sys
import time

import numpy as np
import cantera as ct


def resolve_composition(gas, comp_str):
    """Parse 'A:0.5,B:0.5' and map bare RMG labels onto Cantera species names."""
    names = gas.species_names
    stripped = {}
    for n in names:
        base = re.sub(r"\(\d+\)$", "", n)
        stripped.setdefault(base, []).append(n)
    comp = {}
    for item in comp_str.split(","):
        key, val = item.rsplit(":", 1)
        key = key.strip()
        if key in names:
            comp[key] = float(val)
        elif key in stripped and len(stripped[key]) == 1:
            comp[stripped[key][0]] = float(val)
        else:
            cands = stripped.get(key, [])
            sys.exit(f"Species '{key}' not found or ambiguous (candidates: {cands}). "
                     f"Use --list-species to see names.")
    return comp


def run(mech, phase, T, P, X, t_end, reactor_type, energy, rtol, atol, max_steps=200000):
    gas = ct.Solution(mech, phase) if phase else ct.Solution(mech)
    gas.TPX = T, P, X
    cls = {"constV": ct.IdealGasReactor, "constP": ct.IdealGasConstPressureReactor}[reactor_type]
    try:  # Cantera >= 3.2 warns unless 'clone' is given; older versions lack it
        r = cls(gas, energy="on" if energy else "off", clone=False)
    except TypeError:
        r = cls(gas, energy="on" if energy else "off")
    contents = getattr(r, "phase", None) or r.thermo  # 'thermo' renamed 'phase' in 3.2
    net = ct.ReactorNet([r])
    net.rtol, net.atol = rtol, atol
    hist = ct.SolutionArray(gas, extra=["t"])
    hist.append(contents.state, t=0.0)
    n = 0
    while net.time < t_end and n < max_steps:
        net.step()
        hist.append(contents.state, t=net.time)
        n += 1
    return gas, hist


def ignition_delay(hist, use="T"):
    """Time of the maximum dT/dt (or dP/dt). Meaningless if nothing ignites."""
    y = hist.T if use == "T" else hist.P
    dydt = np.gradient(y, hist.t)
    return hist.t[int(np.argmax(dydt))]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mech", help="Cantera YAML file, e.g. cantera/chem_annotated.yaml")
    ap.add_argument("--phase", default=None, help="phase name (default: first phase, 'gas' for RMG files)")
    ap.add_argument("--list-species", action="store_true")
    ap.add_argument("-T", type=float, default=1000.0, help="initial temperature [K]")
    ap.add_argument("-P", type=float, default=ct.one_atm, help="initial pressure [Pa]")
    ap.add_argument("-X", default=None, help="mole fractions 'A:0.5,B:0.5'")
    ap.add_argument("--t-end", type=float, default=1.0, help="end time [s]")
    ap.add_argument("--reactor", choices=["constV", "constP"], default="constV")
    ap.add_argument("--isothermal", action="store_true", help="energy equation off")
    ap.add_argument("--rtol", type=float, default=1e-9)
    ap.add_argument("--atol", type=float, default=1e-15)
    ap.add_argument("--scan-rtol", action="store_true", help="ignition delay vs rtol 1e-15..1e-3")
    ap.add_argument("--out", default=None, help="prefix for <out>.csv and <out>.png")
    ap.add_argument("--plot-tol", type=float, default=1e-3, help="plot species whose max X exceeds this")
    a = ap.parse_args()

    gas = ct.Solution(a.mech, a.phase) if a.phase else ct.Solution(a.mech)
    if a.list_species:
        print(f"{gas.n_species} species, {gas.n_reactions} reactions")
        print("\n".join(gas.species_names))
        return
    if not a.X:
        sys.exit("Give initial composition with -X")
    X = resolve_composition(gas, a.X)
    use = "P" if a.reactor == "constV" else "T"

    if a.scan_rtol:
        print(f"{'rtol':>8} {'tau [s]':>14} {'wall [s]':>9}")
        for rtol in np.logspace(-15, -3, 13):
            t0 = time.time()
            try:
                _, h = run(a.mech, a.phase, a.T, a.P, X, a.t_end, a.reactor, not a.isothermal, rtol, a.atol)
                print(f"{rtol:8.0e} {ignition_delay(h, use):14.6e} {time.time() - t0:9.2f}")
            except ct.CanteraError as e:
                print(f"{rtol:8.0e} {'FAILED':>14}  {str(e).splitlines()[0][:60]}")
        return

    gas, hist = run(a.mech, a.phase, a.T, a.P, X, a.t_end, a.reactor, not a.isothermal, a.rtol, a.atol)
    print(f"steps: {len(hist.t)}  final T = {hist.T[-1]:.1f} K  final P = {hist.P[-1]:.4g} Pa")
    print(f"ignition delay (max d{use}/dt): {ignition_delay(hist, use):.6e} s")
    if a.out:
        hist.save(a.out + ".csv", basis="mole", overwrite=True)
        print(f"wrote {a.out}.csv")
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))
        ax1.plot(hist.t, hist.T)
        ax1.set_xlabel("t [s]"); ax1.set_ylabel("T [K]")
        keep = [i for i in range(gas.n_species) if hist.X[:, i].max() > a.plot_tol]
        for i in keep:
            ax2.plot(hist.t, hist.X[:, i], label=gas.species_names[i])
        ax2.set_xlabel("t [s]"); ax2.set_ylabel("mole fraction"); ax2.legend(fontsize=7)
        fig.tight_layout(); fig.savefig(a.out + ".png", dpi=120)
        print(f"wrote {a.out}.png")
        # top-10 reactions by peak |net rate of progress| (recomputed along the history)
        rop = np.array([np.abs(hist[i].net_rates_of_progress) for i in range(0, len(hist.t), max(1, len(hist.t) // 500))])
        top = np.argsort(rop.max(axis=0))[::-1][:10]
        print("top reactions by peak |net ROP|:")
        for j in top:
            print(f"  {rop[:, j].max():10.3e}  {gas.reaction(j).equation}")


if __name__ == "__main__":
    main()
