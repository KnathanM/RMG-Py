---
name: rmg-simulate-cantera
description: Simulates RMG-generated mechanisms in Cantera (and RMG's own simple reactor). Covers finding or creating the Cantera YAML (cantera/chem_annotated.yaml, or ck2yaml when a run died before finishing), batch-reactor runs (constant V or P, adiabatic or isothermal), ignition delay, species and rate-of-progress plots, tolerance-convergence checks, gas+surface (SURF0) simulations, RMG's scripts/simulate.py, sensitivity analysis inside RMG, and the rmgpy.tools.canteramodel wrapper. Use when the user says "simulate my RMG model", "run Cantera on chem.yaml", "ignition delay", "batch reactor", "plot mole fractions", "rate of progress", "convert chemkin to yaml", "ck2yaml", "no cantera folder", "species not found H2(1)", "tolerance study", "sensitivity analysis in RMG", or "simulate.py".
---

# Simulating RMG models with Cantera

Based on the 2025 RMG Workshop talk “Simulating RMG Models” and RMG-Py 3.3.0.

Run all commands in the RMG conda env (`rmg_env`) or the Docker container. See **rmg-install** to work out which you have and where `$RMG_PY` is. This checkout requires Cantera ≥ 3.0 (`environment.yml`); the local env has 3.2. The workshop demo used Cantera 2.6, so older notebooks may need small API changes.

## 1. Find the mechanism files

| You have | Use |
|---|---|
| A finished gas-phase run | `RUN/cantera/chem_annotated.yaml` (same chemistry as `chem.yaml`, plus source comments) |
| A finished surface run | `RUN/cantera/chem_annotated.yaml`. This single file holds a `gas` phase and a surface phase named **`SURF0`** (built from `chemkin/chem_annotated-gas.inp` + `-surface.inp`) |
| A run that died or hit walltime (no `cantera/` folder) | Convert the latest Chemkin files yourself with ck2yaml (below) |
| RMS instead of Cantera | `RUN/rms/chemN.rms`. Use the file with the largest N; see **rmg-rms** |

RMG writes `cantera/*.yaml` **only at the end of a run** (`rmgpy/rmg/main.py`, `generate_cantera_files`). Chemkin files are written every iteration: `chemkin/chem_annotated.inp` holds the latest core, and `chemkin/chemNNNN.inp` hold snapshots.

### Convert a Chemkin file manually (ck2yaml)

```bash
cd RUN
# gas phase
ck2yaml --input=chemkin/chem_annotated.inp --transport=chemkin/tran.dat \
        --output=chem_annotated.yaml --permissive
# gas + surface
ck2yaml --input=chemkin/chem_annotated-gas.inp --surface=chemkin/chem_annotated-surface.inp \
        --transport=chemkin/tran.dat --output=chem_annotated.yaml --permissive
```

`--permissive` matches what RMG itself does. If the transport file causes an error, drop `--transport`, as RMG does. Write the output somewhere other than `RUN/cantera/` so you don't overwrite RMG's own files.

## 2. Species names: the #1 gotcha

Cantera names are RMG labels **plus an index suffix**, e.g. `H2(1)`, `O2(2)`, `[OH](5)`. Unindexed inerts such as `Ar`, `N2`, `He`, `Ne` have no suffix. The numbers change from run to run and version to version: the workshop showed `H2(2)`/`O2(3)`, while this version's superminimal gives `H2(1)`/`O2(2)`. Labels you set in the input file still get suffixes.

- **Never hard-code names.** List them first: `python templates/cantera_batch.py RUN/cantera/chem_annotated.yaml --list-species`, or check `gas.species_names`.
- The same label can appear twice with different structures. Superminimal has `O2(2)` (triplet) and `O2(11)` (singlet). Check `chemkin/species_dictionary.txt` to confirm the structure.
- To keep names stable across reruns, define every important species explicitly in the RMG input file.
- RMS `.rms` files use labels **without** suffixes (`H2`, `[OH]`). Surface species may be named differently in Chemkin/Cantera (`CHOX(32)`) than in RMS (`O=[CH][Pt]`).

## 3. Batch reactor: use the tested template

`templates/cantera_batch.py` was tested on superminimal output with Cantera 3.2. It loads the YAML, sets TPX, runs an `IdealGasReactor` (constant V) or `IdealGasConstPressureReactor` with energy on or off, steps a `ReactorNet`, and records a `SolutionArray`. It then reports ignition delay as the time of max dP/dt (constant V) or max dT/dt (constant P), writes CSV and PNG files, and prints the top reactions by peak |net rate of progress|. Bare labels (`H2`) are resolved to `H2(1)` only when the match is unambiguous.

```bash
T=$RMG_PY/.claude/skills/rmg-simulate-cantera/templates/cantera_batch.py
python $T RUN/cantera/chem_annotated.yaml --list-species
python $T RUN/cantera/chem_annotated.yaml -T 1000 -P 1e5 -X "H2:0.67,O2(2):0.33" --t-end 1 --out sim
python $T RUN/cantera/chem_annotated.yaml -T 1000 -P 1e5 -X "H2:0.67,O2(2):0.33" --reactor constP --isothermal
python $T RUN/cantera/chem_annotated.yaml -T 1000 -P 1e5 -X "H2:0.67,O2(2):0.33" --scan-rtol
```

Verified result: superminimal at 1000 K and 1 bar in constant V gives τ ≈ 0.450 s, matching the talk's 0.44 s and RMS's 0.4505 s. Copy the template next to the user's work and adapt it; don't edit the skill copy for a single job.

The core loop, if you'd rather write it inline:

```python
import cantera as ct, numpy as np
gas = ct.Solution("RUN/cantera/chem_annotated.yaml")          # phase 'gas'
gas.TPX = 1000.0, 1e5, {"H2(1)": 0.67, "O2(2)": 0.33}
r = ct.IdealGasReactor(gas, energy="on", clone=False)          # drop clone= on Cantera < 3.2
net = ct.ReactorNet([r]); net.rtol, net.atol = 1e-9, 1e-15
hist = ct.SolutionArray(gas, extra=["t"])
while net.time < 1.0:
    net.step(); hist.append(r.phase.state, t=net.time)         # r.thermo on Cantera < 3.2
tau = hist.t[np.argmax(np.gradient(hist.P, hist.t))]           # ignition delay
# hist.T, hist.P, hist.X (n_t x n_species); gas.net_rates_of_progress = current state only
```

Analysis tips from the talk:
- Plot rates of progress on a **log** scale. On a linear scale nothing shows until ignition.
- Ask which reactions matter **at which time**, because different chemistry dominates at different times.
- Always look at the plot to confirm the computed τ is really the pressure or temperature jump.
- GRI-Mech 3.0 ships with Cantera (`ct.Solution("gri30.yaml")`). Use it only to test code; its chemistry is decades out of date.
- In Jupyter, `!cmd` runs a shell command. Inside Docker, Jupyter needs a published port (`-p 8888:8888`) and `--no-browser --allow-root` (see **rmg-install**).

## 4. Check tolerance convergence

Scan `rtol` (the talk used 1e-15 to 1e-3), as `--scan-rtol` does, and look for the plateau. Tighter tolerances cost more time. Converged answers can need tighter tolerances at higher pressure. **If the solver crashes, try a tighter tolerance as well as a looser one.** Sometimes only a tighter tolerance fixes it. Don't spend compute on tolerances tighter than the plateau.

## 5. Gas + surface in Cantera (tested on minimal_surface output)

```python
import cantera as ct
y = "RUN/cantera/chem_annotated.yaml"
gas  = ct.Solution(y, "gas")
surf = ct.Interface(y, "SURF0", [gas])          # check the phase name: grep -A1 '^- name' the yaml
gas.TPX = 1000.0, ct.one_atm, {"CH4(1)": 0.15, "O2(2)": 0.15, "N2": 0.7}
surf.TP = 1000.0, ct.one_atm; surf.coverages = {"X(3)": 1.0}
r = ct.IdealGasReactor(gas, energy="off", clone=False); r.volume = 1e-6
rs = ct.ReactorSurface(surf, r, A=1e5 * r.volume, clone=False)   # A/V = surfaceVolumeRatio
net = ct.ReactorNet([r]); net.rtol, net.atol = 1e-10, 1e-20
net.advance(0.1); print(dict(zip(surf.species_names, surf.coverages)))
```

Older RMG versions wrote an unnamed SITE block, which ck2yaml names `surface1`. Always read the phase name from the file.

## 6. Other ways to simulate

| Tool | When | Notes |
|---|---|---|
| `scripts/simulate.py INPUT CHEMKIN DICTIONARY [--no-dlim] [-f]` | Quick re-simulation with RMG's own reactor, using the reactor blocks in an RMG input file | Writes `solver/simulation_*.csv/png` and `simulate.log` next to INPUT. Runs sensitivity if the reactor has `sensitivity=`, and uncertainty if there is an `uncertainty()` block. RMG simple batch reactors only (no flow or geometry). Example: `examples/scripts/simulate/sensitivity/` |
| Sensitivity during an RMG run | Ranking the kinetics/thermo that matter for one species | `simpleReactor(..., sensitivity=['ethane'], sensitivityThreshold=0.01)` (also `sensitivityTemperature/Pressure/MoleFractions` for ranged reactors) or `liquidReactor(sensitivity=...)`. Tolerances: `simulator(atol, rtol, sens_atol=1e-6, sens_rtol=1e-4)`. Output: `solver/sensitivity_1_SPC_1.csv` and `_reactions.png`/`_thermo.png`. `surfaceReactor` and the RMS reactors **cannot** do this. Example: `examples/rmg/minimal_sensitivity/` |
| `rmgpy.tools.canteramodel.Cantera` | Driving Cantera from RMG `Species`/`Reaction` objects, perturbing thermo or kinetics | See `reference/canteramodel.md` (tested recipe and two bugs) |
| RMS (Julia) | Fast sensitivities (transitory/adjoint), flux diagrams, mechanism analysis | **rmg-rms** |
| `scripts/generateFluxDiagram.py` | Flux-diagram movie | **rmg-scripting-tools** (single condition only) |

Relevant notebooks in `ipython/`: `cantera_simulation.ipynb` (wrapper), `combustion_model_and_ignition_delay_demo.ipynb` (builds and runs an RMG model, then computes ignition delay and sensitivity), `cantera_sensitivity_comparison.ipynb`, `mechanism_analyzer.ipynb` (pathway analysis from a Chemkin `.ckcsv`, via `rmgpy.tools.ckcsvparser`), `local_uncertainty.ipynb`, `global_uncertainty.ipynb`. The workshop notebook `Session_8_simulation_superminimal_cantera` is not in the repo; section 3 reconstructs it.

## 7. Background on sensitivity and uncertainty (from the talk)

- Cantera's built-in approach is brute-force or forward local sensitivity: perturb each parameter and re-simulate. RMS is much faster for large models; see **rmg-rms**.
- To find which parameters are worth improving, compare sensitivity with uncertainty. RMG can estimate parameter uncertainties (`uncertainty()` block; see `ipython/local_uncertainty.ipynb`). The presenter said updates to this were still being merged at the time of the talk.

## Agent notes

- Don't write into the user's `RUN/cantera/`. Write new YAML, CSV and plots to a separate folder, or confirm with the user first.
- Simulations of large mechanisms with tight tolerances or rtol scans can take a long time. Run them in the background and tell the user what is running.
- Before you report results, show the user the species names you chose (with their suffixes).

**When unsure:** check `rmgpy/rmg/main.py` (`generate_cantera_files`), `rmgpy/chemkin.pyx` (`SITE/SURF0/`), `rmgpy/tools/canteramodel.py`, `rmgpy/tools/simulate.py`, `rmgpy/rmg/input.py` (`simple_reactor`, `simulator`), and `ck2yaml --help`.
