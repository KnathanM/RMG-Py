---
name: rmg-run-job
description: Writes an RMG-Py input.py and runs, monitors and restarts RMG mechanism-generation jobs. Covers the database, species, simpleReactor/liquidReactor/ranged reactors, termination, simulator, model, options and generatedSpeciesConstraints blocks; the rmg.py command-line flags (-t wall time, -i, -n, -o, -r, -k, -q/-v/-d, -p); running in the background and reading RMG.log; the output folder layout; and restarting from a seed. Use it when the user says "run RMG", "set up an RMG input file", "generate a mechanism for my fuel", "my RMG job is stuck / did it finish", "what does this RMG.log message mean", "restart my RMG run", "where is chem.inp / chem.yaml", or asks about input.py keywords and defaults.
---

# Running RMG jobs

Based on the 2025 RMG Workshop talk “Running RMG Jobs” and RMG-Py 3.3.0.

Related skills:
- First-time sanity run: `rmg-first-job`.
- Install and environment detection: `rmg-install`.
- Choosing libraries: `rmg-database`.
- Pressure dependence: `rmg-pressure-dependence`.
- Pruning, filtering, staging and branching: `rmg-advanced-settings`.
- Surface reactors: `rmg-catalysis`.
- RMS (Julia) reactors: `rmg-rms`.
- What to do with the result: `rmg-simulate-cantera`, `rmg-model-building-strategy`.

## 0. Know how RMG is invoked here
Use `rmg-install` (its `templates/detect_rmg_env.sh`) to find `$RMG_PY` and the Python interpreter.
- **Conda/source install:** activate `rmg_env` (the prompt must not say `(base)`), then run `python $RMG_PY/rmg.py ...`. rmgpy may not be pip-installed; `rmg.py` works anyway because it sits next to `rmgpy/`.
- **Docker:** inside the container the shell starts in `/rmg/RMG-Py` with `rmg_env` active. Run `python /rmg/RMG-Py/rmg.py ...`. Put job directories under the bind-mounted folder (e.g. `/rmg/RMG-Py/myrmgfiles/`), or the files will not be visible on the host.

## 1. Gather the minimum facts before writing input.py
Ask the user, or confirm, the following. `rmg-model-building-strategy` has the full list.
- Phase: gas, liquid (which solvent), or surface (go to `rmg-catalysis`).
- Starting species and their structures: SMILES, or an adjacency list for anything ambiguous. See `rmg-molecule-representation`.
- Conditions: T, P (or concentrations) and mixture. Experiment time scale or target conversion.
- Chemistry type: oxidation or pyrolysis. Elements present (N, S, halogens?). Any trusted libraries the user already uses.
- Compute budget: how long the run may take, and how much RAM.

## 2. Make a fresh job directory (never reuse one)
RMG writes outputs **next to the input file**, unless you give `-o DIR`. Re-running in a used directory overwrites the previous results:
- `RMG.log` is moved to `RMG_backup.log`, which keeps only one backup.
- `pdep/`, `solver/`, `kinetics_database/` and `seed/` are **deleted**.
- `chemkin/` files are overwritten.

```bash
JOB=$HOME/rmg_runs/propane_ox_1000K_v1      # one directory per job and per variant
[ -e "$JOB" ] && echo "EXISTS - choose a new name" || mkdir -p "$JOB"
cp $RMG_PY/.claude/skills/rmg-run-job/templates/input_gas_phase.py "$JOB/input.py"
```
Then edit `$JOB/input.py`. The template is a commented gas-phase combustion/pyrolysis start: seed + matching thermo, pdep on, filtering on, constraints with `allowed`. Other starting points are in `$RMG_PY/examples/rmg/`:
- `commented/input.py`: every option annotated.
- `superminimal`, `minimal`, `ethane-oxidation`, `liquid_phase`.
- `pruning_test`, `propane_branching`, `minimal_staged`.

## 3. Write input.py
Every keyword and default is in [reference/input-file-cheatsheet.md](reference/input-file-cheatsheet.md). The essentials:

```python
database(thermoLibraries=['primaryThermoLibrary'], reactionLibraries=[], seedMechanisms=[],
         kineticsDepositories=['training'], kineticsFamilies='default', kineticsEstimator='rate rules')
species(label='fuel', reactive=True, structure=SMILES("CCC"))
species(label='O2', structure=SMILES("[O][O]"))              # triplet O2
species(label='N2', reactive=False, structure=SMILES("N#N"))  # bath gas
simpleReactor(temperature=(1000,'K'), pressure=(1.0,'bar'),
              initialMoleFractions={'fuel':0.04, 'O2':0.20, 'N2':0.76},
              terminationConversion={'fuel':0.9}, terminationTime=(1,'s'))
simulator(atol=1e-16, rtol=1e-8)
model(toleranceMoveToCore=0.1, toleranceInterruptSimulation=0.1, filterReactions=True)
generatedSpeciesConstraints(allowed=['input species','seed mechanisms','reaction libraries'],
                            maximumRadicalElectrons=2)
options(units='si', generateSeedEachIteration=True)
```

Rules that matter:
- **The file has no Python builtins.** You cannot use `import`, `float('inf')` or `range()`. A builtin call fails as `TypeError: 'NoneType' object is not subscriptable`.
- **Libraries:** the first library that has a species or reaction wins, so put the most trusted first.
  - Seed mechanisms go into the core; reaction libraries go into the edge.
  - Pair each seed with its own thermo (e.g. `BurkeH2O2` thermo with the `BurkeH2O2inN2` seed; `Klippenstein_Glarborg2016` for both).
  - For combustion, always seed the H2/O2 chemistry. Don't use oxidation seeds for pyrolysis.
- **Species:** every listed species enters the core. List the fuel, the oxidizer and any species you expect, so names stay stable between runs.
  - RMG always adds Ar, He, Ne and N2 as inert species.
- **Reactors:** you need at least one, and each needs at least one termination criterion.
  - `simpleReactor`: isothermal, isobaric batch reactor.
  - Several reactor blocks are logged as `reaction system 1, 2, ...`.
  - **Ranged reactor:** `temperature=[(800,'K'),(1400,'K')]`, `pressure=[(1,'bar'),(10,'bar')]`, `initialMoleFractions={'fuel':[0.02,0.06], ...}`. Add `nSims` of at least 2+N (up to 2+5N) for N ranged dimensions.
    - It counts as one reaction system. Conditions are drawn by weighted stochastic sampling, not a regular grid.
    - Add `balanceSpecies='N2'` to put the slack into N2 instead of renormalizing everything. The balance species itself cannot be a range.
  - **Liquid:** `liquidReactor(temperature=..., initialConcentrations={'x':(c,'mol/cm^3')}, terminationTime=...)` plus a `solvation(solvent='octane')` block. This is a native RMG reactor, not an RMS one.
  - **Surface:** `rmg-catalysis`. **RMS reactors** (`constantTPIdealGasReactor`, …): `rmg-rms`.
- **Termination is OR.** Whichever of `terminationConversion`, `terminationTime` or `terminationRateRatio` is reached first ends that simulation.
  - Never rely only on a conversion that equilibrium may prevent. The job would never converge. Add a `terminationTime`.
  - The conversion species needs a non-zero initial amount.
- **model():** `toleranceMoveToCore` is required. It is relative to the characteristic flux.
  - Start at about 0.1 and tighten later.
  - Keep `toleranceInterruptSimulation` equal to MoveToCore unless you are pruning (then ~1e8; see `rmg-advanced-settings`). The interrupt tolerance cannot be below MoveToCore.
- **Pressure dependence is off unless you add `pressureDependence()`.** It is needed for almost all gas-phase work. See `rmg-pressure-dependence`.
- **Always include** `allowed=['input species','seed mechanisms','reaction libraries']` in `generatedSpeciesConstraints`. Without it, a seed or library species that breaks a constraint aborts the run.

## 4. Parse-check before launching (seconds, no database load)
```bash
cd $RMG_PY && python -c "
from rmgpy.rmg.main import RMG; from rmgpy.rmg.input import read_input_file
r = RMG(input_file='$JOB/input.py'); read_input_file('$JOB/input.py', r)
r.output_directory = '$JOB'; r.check_input(); print('input OK:', len(r.reaction_systems), 'reactor(s)')"
```
This catches syntax errors, missing tolerances, missing termination criteria, bad constraint keys, and pdep range or bath-gas problems. It does **not** check library names; those fail at database load, about a minute into the run.

## 5. Launch in the background with a wall time
**Ask the user before** starting a run expected to take more than about an hour, or settings likely to need a lot of RAM.

```bash
cd "$JOB"
nohup python $RMG_PY/rmg.py -t 00:04:00:00 input.py > stdout.log 2>&1 &
echo $! > rmg.pid
```
- Use **`-t DD:HH:MM:SS`** (lowercase; the talk said `-T`).
  - `options(wallTime=...)` is ignored when you run `rmg.py`, because the CLI default `00:00:00:00` overwrites it.
  - RMG stops early if it predicts the next iteration would overrun. It checks only between iterations, so for a hard cap also wrap it with `timeout`.
- Give every run you plan to compare the same `-t`, so comparisons are fair. Make sure the limit doesn't cut off needed chemistry.
- For a quick smoke test, use `-i 3` (stop after 3 iterations).

CLI flags (`rmgpy/util.py`):

| flag | meaning |
|---|---|
| `-t DD:HH:MM:SS` | Wall time (graceful stop) |
| `-i N` | Maximum number of iterations |
| `-n N` | Processes for reaction generation only. About 6 gives roughly 2x early in a run; no help when the ODE is the bottleneck. It is also capped by free RAM and must be ≤ the CPU count |
| `-o DIR` | Output directory (default: the input file's directory) |
| `-r DIR` | Restart from a seed folder (the one containing `seed/`, `seed_edge/`, `filters/`) |
| `-k` | Write `kinetics_database/` with the sources of each family's entries |
| `-q` / `-v` / `-d` | Quiet / verbose / debug logging (mutually exclusive). `-v` and `-d` make huge logs |
| `-p` / `-P` | Profile with cProfile / postprocess an existing profile |

## 6. Monitor without blocking
Poll occasionally; don't tail -f in the foreground. Meanings and actions for each message are in [reference/log-messages.md](reference/log-messages.md).
```bash
kill -0 $(cat rmg.pid) 2>/dev/null && echo running || echo stopped
grep -E "The model (core|edge) has" RMG.log | tail -n 2
grep -E "Execution time|Memory used" RMG.log | tail -n 2
grep -E "exceeded the minimum rate for moving to model core" RMG.log | tail -n 5
grep -nE "MODEL GENERATION|Traceback|Error" RMG.log | tail -n 5
```
Warning signs:
- Edge growing by tens of thousands of species per iteration.
- Memory approaching the machine's RAM.
- Strange species entering the core (usually bad thermo).
- Repeated `Resurrecting Model...`.
Options for each are in `rmg-advanced-settings`.

## 7. Decide whether it finished
| last lines of RMG.log | status |
|---|---|
| `MODEL GENERATION COMPLETED`, `The final model core has N species and M reactions` | Done. `cantera/chem.yaml` written; collision check done |
| `MODEL GENERATION TERMINATED` + `not enough time ... wall time` | Stopped by `-t`. Chemkin and seed are usable; there is no `cantera/` |
| `MODEL GENERATION TERMINATED` + `maximum number of iterations` | Stopped by `-i` |
| A traceback | Crashed. Fix the cause, then restart from `seed/` |
| Nothing new, process gone | Probably killed for running out of memory |

A run doesn't need to "complete" to be useful. What matters is whether the target predictions have converged as the model grows (`rmg-model-building-strategy`).

After any finish, check the following:
- `collision_rate_violators.log`. It is written only at normal completion, and only when there are violators.
- The first 30–50 core species, for sanity.
- That `chemkin/species_dictionary.txt` is kept with the mechanism.

## 8. Output layout (in the job directory)
| path | contents |
|---|---|
| `RMG.log` | Full log: git commits of RMG-Py and RMG-database, an echo of the input, every enlargement step |
| `chemkin/chem.inp`, `chem_annotated.inp` | Final or latest core mechanism. The annotated file has a source comment per reaction and per species |
| `chemkin/species_dictionary.txt` | Adjacency lists. Labels like `S(123)` are only meaningful together with this file |
| `chemkin/tran.dat` | Transport data. Pass it to `ck2yaml` if you convert by hand |
| `chemkin/chemNNNN.inp` | Snapshot when the core had NNNN species |
| `chemkin/chem_edge*.inp`, `output_edge.html` | Edge mechanism; only with `saveEdgeSpecies=True` |
| `cantera/chem.yaml`, `chem_annotated.yaml` | Written **only at normal completion** |
| `rms/chemN.rms` | RMS-format snapshots |
| `output.html` + `species/*.png` | Only with `generateOutputHTML=True` |
| `seed/{seed,seed_edge,filters}/` | Restart point, in RMG library format, rewritten each iteration |
| `restart_from_seed.py` | The input file with `restartFromSeed(path='seed')` prepended (not written by restart jobs) |
| `solver/` | `simulation_<sys>_<ncore>.csv/.png` (with `saveSimulationProfiles`) and `sensitivity_*.csv` |
| `pdep/networkN_M.py` | Arkane-format pdep networks (`rmg-pressure-dependence`) |
| `statistics.xls`, `plot/` | Core/edge size, memory and time per iteration (`plot/` needs `generatePlots`) |
| `collision_rate_violators.log` | Core reactions faster than the collision limit |
| `previous_restart/` | Copy of the seed this job restarted from |

To use an unfinished run in Cantera:
```bash
python -m cantera.ck2yaml --input=chemkin/chem_annotated.inp --transport=chemkin/tran.dat --output=chem.yaml --permissive
```

## 9. Restart from a seed (crash, wall time, or to continue with new settings)
Use a **new** directory, so the old run stays intact:
```bash
NEW=${JOB}_restart1; mkdir "$NEW"; cp "$JOB/input.py" "$NEW/"       # edit settings if desired
cd "$NEW" && nohup python $RMG_PY/rmg.py -r "$JOB/seed" -t 00:04:00:00 input.py > stdout.log 2>&1 &
```
- Instead of `-r`, you can add `restartFromSeed(path='/abs/path/to/old/seed')` at the top of `input.py`. Relative paths are resolved from the input file's directory. `$JOB/restart_from_seed.py` is a ready-made copy for restarting in place.
- RMG copies the seed into `previous_restart/` before overwriting anything.
- Keep `generateSeedEachIteration=True` (the default), so a usable seed always exists.

## Gotchas (the talk vs RMG-Py 3.3.0)
- The wall-time flag is `-t`, not `-T`. `options(wallTime=)` has no effect under `rmg.py`.
- `toleranceMoveToCore` has no default (it is required). 0.1 appears only in examples.
- `toleranceKeepInEdge` defaults to 0 (no pruning).
- `maximumEdgeSpecies` defaults to 1,000,000, not 100,000.
- Species constraints are **unlimited by default**, except `maximumSingletCarbenes=1` and `maximumCarbeneRadicals=0`. They are not "reasonable defaults".
- `maximumIsotopicAtoms` (listed in `input.rst`) raises `InputError`.
- He, Ar and Ne in the output come from RMG auto-adding Ar, He, Ne and N2 as inert species, not from `primaryThermoLibrary`.
- `liquidReactor` is a native RMG reactor, not an RMS reactor.
- `filterThreshold` defaults to 1e8 in the code; the docs say 5e8.
- The built-in sensitivity in `simpleReactor` works, but the presenter suggested RMS or Cantera tools for sensitivity work (`rmg-simulate-cantera`, `rmg-rms`).

## When unsure
Read the code; it is the source of truth:
- `rmgpy/rmg/input.py`: every block, keyword and default.
- `rmgpy/util.py`: CLI flags.
- `rmgpy/rmg/main.py`: run loop, outputs, end messages.
- `rmgpy/solver/base.pyx`: termination and flux logic.
- `documentation/source/users/rmg/input.rst` and `running.rst`.
- `examples/rmg/*/input.py`.
