---
name: rmg-rms
description: Uses ReactionMechanismSimulator.jl (RMS) with RMG. Covers checking whether RMS/Julia is installed, installing it with install_rms.sh, the rms/chemN.rms files RMG writes, the RMS-backed reactors in RMG input files (constantVIdealGasReactor, constantTPIdealGasReactor, liquidSurfaceReactor, constantTVLiquidReactor), and simulating from Python via juliacall (phases, domains, interfaces, CVODE_BDF), with mole-fraction plots, flux diagrams, rates of production, transitory/adjoint/threaded-forward sensitivity, automatic mechanism analysis (analyzespc), and multiphase gas-surface catalysis. Use when the user says "RMS", "Reaction Mechanism Simulator", "Julia", "juliacall", "chem13.rms", "transitory sensitivity", "adjoint sensitivity", "RMS flux diagram", "rate of production", "constantVIdealGasReactor", "install RMS", "No module named juliacall", or wants fast sensitivity analysis of an RMG model.
---

# Using RMS (ReactionMechanismSimulator.jl) with RMG

Based on the 2025 RMG Workshop talk “Using RMS” and RMG-Py 3.3.0.

RMS is a separate Julia package, and it is **optional**. Plain RMG runs work without it, because Julia is only loaded the first time it is needed (`LazyMain` in `rmgpy/rmg/reactionmechanismsimulator_reactors.py`). Without RMS you lose the four RMS reactors listed below, the RMS simulation and sensitivity tools, and the SLS master-equation method (`rmgpy/pdep/sls.py`).

## 1. Is RMS installed? (read-only checks)

```bash
conda activate rmg_env          # or inside Docker
python -c "from juliacall import Main as jl; jl.seval('using ReactionMechanismSimulator'); print('RMS OK')"
julia --version                 # must be 1.10.x
julia --project="$CONDA_PREFIX/julia_env" -e 'using ReactionMechanismSimulator; println(pkgversion(ReactionMechanismSimulator))'
conda env config vars list      # install_rms.sh sets JULIA_* / PYTHON_JULIAPKG_* here
```

`ModuleNotFoundError: No module named 'juliacall'` means RMS is not installed in this env. An RMG input that uses an RMS reactor then fails while the input file is read. The first `using ReactionMechanismSimulator` can take about 5 minutes of compilation; later calls take about a minute.

## 2. Installing (ask the user first)

The install changes the conda env: it sets env vars, conda-installs `pyjuliacall`, and downloads many Julia packages. Get the user's OK before running it.

```bash
cd $RMG_PY && conda activate rmg_env
source install_rms.sh                         # "standard": interactive y/N prompt to confirm the env
RMS_INSTALLER=continuous source install_rms.sh            # non-interactive
RMS_BRANCH=for_rmg source install_rms.sh                  # default branch is for_rmg
RMS_INSTALLER=developer RMS_PATH=/path/to/ReactionMechanismSimulator.jl source install_rms.sh
```

- The script must be **sourced**, not run with `bash`.
- It needs **juliaup** and **Julia 1.10** exactly. If either is missing it prints the fix and stops (`curl -fsSL https://install.julialang.org | sh`, restart the shell, then `juliaup add 1.10; juliaup default 1.10; juliaup remove release`). Fix the problem and source it again. Expect several rounds.
- It sets `JULIA_CONDAPKG_BACKEND=Null`, `JULIA_PYTHONCALL_EXE`, `PYTHON_JULIAPKG_EXE` and `PYTHON_JULIAPKG_PROJECT=$CONDA_PREFIX/julia_env`. Re-activate the env afterwards.
- Docker: per the talk, the workshop image (3.2.0) already includes an RMS version (v1.0.x). Check it with the commands in section 1. See **rmg-install** for detection in general.
- For parallel pytest (`-n auto`), use an env *without* Julia (`pytest.ini`).

## 3. RMS files from an RMG run

RMG always writes `RUN/rms/chem{N}.rms` (YAML), where N is the number of core species, after each iteration, whether or not RMS is installed. **Use the largest N** (e.g. `chem13.rms` for superminimal); that is the final model. `rms.readinput` also reads Chemkin: `rms.readinput("chem_annotated.inp", spcdict="species_dictionary.txt")`.

Species names in `.rms` are RMG labels **without** the `(n)` suffix: `H2`, `[OH]`, `X`, `COX`. Cantera names have the suffix (`H2(1)`). Some adsorbates get different names in the two formats (`CHOX(32)` in Chemkin vs `O=[CH][Pt]` in RMS). Read the names from `sim.names`.

## 4. RMS reactors inside an RMG input file

| Keyword (`rmgpy/rmg/input.py`) | RMS class | Arguments |
|---|---|---|
| `constantVIdealGasReactor` | ConstantVIdealGasReactor (adiabatic) | `temperature, pressure, initialMoleFractions, terminationConversion, terminationTime, terminationRateRatio, balanceSpecies` |
| `constantTPIdealGasReactor` | ConstantTPIdealGasReactor | same as above |
| `liquidSurfaceReactor` | ConstantTLiquidSurfaceReactor | `temperature, initialConcentrations, initialSurfaceCoverages, surfaceVolumeRatio, distance, viscosity, surfPotential, liqPotential, termination*, constantSpecies`. Needs `solvation()` and `catalystProperties()` (see **rmg-catalysis**) |
| `constantTVLiquidReactor` | ConstantTVLiquidReactor | `temperature, initialConcentrations, liquidVolume, residenceTime, inletVolumetricFlowRate, outletVolumetricFlowRate, inletConcentrations, vaporPressure, vaporMoleFractions, termination*, constantSpecies` |

Rules (verified in code):
- **No ranges.** A list for T, P or concentrations raises `InputError: Condition ranges not supported for this reaction type`. Use several reactor blocks instead.
- **No sensitivity argument.** Run sensitivity afterwards in RMS (section 6).
- `options(saveSimulationProfiles=True)` with an RMS reactor raises `InputError` (`main.py`).
- These keywords are not documented in `documentation/source/users/rmg/input.rst`. Use `input.py` and the examples: `examples/rmg/rms_constant_V/input.py`, `examples/rmg/liquid_cat/`, `examples/rmg/CO2RR/`.
- Bug in this version: `liquidSurfaceReactor(viscosity=...)` stores `distance` as the viscosity (`input.py`, `liquid_cat_reactor`), so `viscosity` is effectively ignored or wrong.

## 5. Simulate from Python with juliacall (single gas phase)

These snippets come from `examples/rmg/superminimal/*_RMS.ipynb` and `examples/rmg/catalysis/ch4_o2/simulate_ch4o2cat_RMS.ipynb`. They were re-run against superminimal and minimal_surface output from this checkout, using a separate env that had RMS 1.0.1 installed. RMS is **not** installed in this machine's `rmg_env`. Run from the RMG run folder:

```python
from juliacall import Main as rms
rms.seval("using PythonCall"); rms.seval("using ReactionMechanismSimulator"); rms.seval("using ReactionMechanismSimulator.Sundials")
from rmgpy.rmg.reactionmechanismsimulator_reactors import to_julia   # Python dict/list -> Julia Dict/Vector
import numpy as np

pd = rms.readinput("rms/chem13.rms")
ig = rms.IdealGas(pd["phase"]["Species"], pd["phase"]["Reactions"], name="gas")
ic = {"T": 1000.0, "P": 1.0e5, "H2": 0.67, "O2": 0.33}             # SI; species values are MOLES
domain, y0, p = rms.ConstantVDomain(phase=ig, initialconds=to_julia(ic))   # adiabatic const V (ignition)
# domain, y0, p = rms.ConstantTPDomain(phase=ig, initialconds=to_julia(ic)) # flow tube / isothermal batch
react = rms.Reactor(domain, y0, (0.0, 1.0), p=p)
sol = rms.solve(react.ode, rms.CVODE_BDF(), abstol=1e-16, reltol=1e-8)
sim = rms.Simulation(sol, domain)

list(sim.names)                                   # species names
rms.molefractions(sim, "O", 1.0)                  # x_H2O at t = 1 s (0.47 here)
iT = domain.thermovariabledict["T"] - 1           # Julia is 1-based: subtract 1 from Python
ts = np.linspace(0, 1, 2001); T = [sol(t)[iT] for t in ts]
rms.plotmolefractions(sim, 0.99, tol=1e-3)        # matplotlib figure; use plt.savefig(...) in scripts
rms.getfluxdiagram(sim, 0.45)                     # writes ./fluxdiagrams/flux_diagram_1.{png,svg,dot}
rms.rops(sim, "[OH]", 0.45)                       # rates of production (numbers)
rms.plotrops(sim, "[OH]", 0.45); rms.plotradicalrops(sim, 0.45)
rms.save(sim, "sim.csv")                          # full solution to CSV
```

Verified result: superminimal at 1000 K and 1 bar in constant V reaches maximum dT/dt at about 0.4505 s, which matches Cantera's 0.4503 s.

Domains (RMS source): `ConstantTPDomain`, `ConstantVDomain`, `ConstantPDomain`, `ParametrizedTPDomain`, `ParametrizedVDomain`, `ParametrizedPDomain` (use these for measured T/P/V traces), `ConstantTVDomain` and `ParametrizedTConstantVDomain` (liquids), and `ConstantTAPhiDomain` (surfaces). Phases: `IdealGas`, `IdealDiluteSolution`, `IdealSurface`. Interfaces: `Inlet`, `Outlet`, `VolumetricFlowRateInlet/Outlet`, `ReactiveInternalInterface(ConstantTPhi)`, `kLAkHCondensationEvaporationWithReservoir`, `VaporLiquidMassTransferInternalInterfaceConstantT`. The talk noted that a steady constant-T, constant-P plug-flow reactor is equivalent to a batch reactor run in time.

## 6. Sensitivity analysis: pick the method

| Need | Method | Call |
|---|---|---|
| Iterating on a model; what matters *now*, and why (pairs with flux/ROP) | **Transitory** (milliseconds; about 18,000× faster than adjoint; not true sensitivities, different units) | `rms.plotrxntransitorysensitivities(sim, "H2", t, N=10, tol=1e-5)`, `rms.plotthermotransitorysensitivities(...)`, `rms.transitorysensitivitiesfullexact(sim, t)` |
| Exact sensitivity of a few targets at one time (e.g. for sensitivity × uncertainty, or for papers) | **Adjoint** | `dps = rms.getadjointsensitivities(sim, "H2", rms.CVODE_BDF(), abstol=1e-6, reltol=1e-3)`, then `rms.plotrateadjointsensitivities(sim, "H2", dps, N=10, tol=1e-5)` and `plotthermoadjointsensitivities` |
| Exact, all targets at all times, or thousands of species | **Threaded forward** | `s = rms.threadedsensitivities(react, odesolver=rms.CVODE_BDF(), senssolver=rms.CVODE_BDF(), odekwargs={rms.Symbol("abstol"):1e-18, rms.Symbol("reltol"):1e-6}, senskwargs={rms.Symbol("abstol"):1e-6, rms.Symbol("reltol"):1e-3})`; `simt = rms.Simulation(s, domain)`; `rms.plotmaxrateforwardsensitivity(simt, "H2", N=10, tol=1e-5)`; `rms.getconcentrationsensitivity(simt, "H2", rxn_index_1based, t)` |
| — | Traditional forward (`rms.Reactor(..., forwardsensitivities=True)`) | **Don't use.** The talk said it is worse than threaded in every way |

Advice from the talk:
- **Don't evaluate sensitivity at a time when no chemistry is happening.** Look at the profiles first, then pick times. For ignition, evaluate *just before* ignition, where radicals build up. Sample several times, because the dominant chemistry changes over time.
- Transitory analysis right at the ignition point can fail with `Could not find a multimodal slice` (reproduced at t = 0.44 s for superminimal; 0.30 s and 0.45 s worked).
- Adjoint uses the end of the simulated `tspan`. To get it at another time, re-simulate to that time.
- Use `CVODE_BDF` in almost every case.
- Sensitivities say *what* matters, not *why*. Reactions in the "too fast" or "too slow" regimes can still matter once you allow for their uncertainty.
- The superminimal sensitivity notebook's last cell plots `sim_tfs` where it should plot `sim_fs`.

**Automatic mechanism analysis** combines transitory sensitivity with branching, path and radical analysis:
```python
ras = rms.analyzespc(sim, "H2", 0.30, N=5, tol=1e-3)   # also branchthreshold=0.9, pathbranchthreshold=0.2, ...
for ra in ras: rms.printrxnanalysis(sim, ra)
```

## 7. Gas + surface (catalysis) domains (tested on minimal_surface output)

```python
pd = rms.readinput("rms/chem29.rms")                 # phases named "gas" and "surface"
ig  = rms.IdealGas(pd["gas"]["Species"], pd["gas"]["Reactions"], name="gas")
sd  = 2.483e-5                                       # site density, mol/m^2 (= 2.483e-9 mol/cm^2)
cat = rms.IdealSurface(pd["surface"]["Species"], pd["surface"]["Reactions"], sd, name="surface")
inter_rxns = rms.get(pd, rms.Set(["surface", "gas"]), rms.nothing)["Reactions"]
T, A = 1000.0, 1.0e5                                 # A in m^2 (value used in testing); gas V follows from moles, T and P, so set A = (A/V)*V yourself
dg, y0g, pg = rms.ConstantTPDomain(phase=ig, initialconds=to_julia({"T": T, "P": 1e5, "CH4": 0.15, "O2": 0.15, "N2": 0.7}))
dc, y0c, pc = rms.ConstantTAPhiDomain(phase=cat, initialconds=to_julia({"T": T, "A": A, "X": sd * A}))  # vacant-site label
inter, pinter = rms.ReactiveInternalInterfaceConstantTPhi(dg, dc, inter_rxns, T, A)
react, y0, p = rms.Reactor((dg, dc), (y0g, y0c), (0.0, 0.1), (inter,), (pg, pc, pinter))
sol  = rms.solve(react.ode, rms.CVODE_BDF(), abstol=1e-20, reltol=1e-8)
ssys = rms.SystemSimulation(sol, (dg, dc), (inter,), p)
gas, surf = ssys.sims[0], ssys.sims[1]               # Python indexing is 0-based, in domain order
rms.molefractions(surf, "COX", 0.01); rms.plotmolefractions(surf, 0.099, tol=1e-3)
rms.getfluxdiagram(ssys, 1e-3); rms.plotrops(ssys, "OX", 1e-3); rms.save(ssys, "cat.csv")
```

The vacant-site key must be your model's label: `X` in minimal_surface, `vacantX` in `catalysis/ch4_o2`. Pass `tf` slightly *below* the end of `tspan` to the plot functions. Otherwise you can get `Solution interpolation cannot extrapolate past the final timepoint`.

## 8. Troubleshooting

- The talk recommends writing RMS code **directly in Julia** when you can: error messages are much clearer, and the Python-wrapper notebooks broke for attendees during the workshop. The Julia equivalents are the same calls without the `rms.` prefix, with `Dict(...)` instead of `to_julia`. See the online RMS documentation.
- The old `pyrms` wrapper is gone. The notebooks now use `juliacall` (`from juliacall import Main as rms`).
- `ValueError: NoneType copy mode not allowed` from `plotrops` and similar comes from a numpy/PythonCall array-conversion mismatch in that env (seen in testing). Use the numeric functions (`rms.rops`, `rms.molefractions`, `rms.concentrations`) and plot with matplotlib yourself, or run in Julia.
- Julia warnings such as "method definition ... declares type variable" are harmless noise.

## Agent notes

- The first Julia call in a session compiles for minutes. Run scripts in the background, and tell the user why it's slow.
- Don't run `install_rms.sh` without explicit user consent, because it changes the conda env.
- `getfluxdiagram` writes `./fluxdiagrams/` and `save` writes CSV files to the cwd. Run from a scratch folder.

**When unsure:** check `install_rms.sh`, `rmgpy/rmg/input.py` (the `constant_*_reactor` and `liquid_cat_reactor` functions), `rmgpy/rmg/reactionmechanismsimulator_reactors.py`, `rmgpy/yml.py` (`RMSWriter`), the `*_RMS.ipynb` notebooks under `examples/rmg/`, and the RMS source or docs for function signatures.
