---
name: rmg-first-job
description: Runs a first RMG smoke-test job (the superminimal H2/O2 example, or `make eg0`/`make eg1`) in a fresh scratch directory, under conda or Docker, and explains what a successful run looks like and which output files appear. Use when the user says "run my first RMG job", "test that RMG works", "run the superminimal example", "smoke test RMG", "make eg1", "did my RMG install work?", "what does RMG output?", or right after installing or updating RMG.
---

# First RMG job (smoke test)

Based on the 2025 RMG Workshop talk “First RMG Job” and RMG-Py 3.3.0.

**Goal:** prove the install works end to end, in under a minute, without polluting the RMG-Py checkout. For real jobs, use the rmg-run-job skill.

## 0. Know how RMG is launched here

If you don't already know the run mode, `$RMG_PY` and the python to use, run the detection step of the rmg-install skill:

```bash
bash .claude/skills/rmg-install/templates/detect_rmg_env.sh
```

| Mode | `$RMG_PY` | Python |
|---|---|---|
| Conda + source | path of the RMG-Py checkout | `rmg_env` python (`conda activate rmg_env`) |
| Docker (inside the container) | `/rmg/RMG-Py` | already active |

First run `python $RMG_PY/rmg.py --help`. It should print the usage line `rmg.py [-h] [-q | -v | -d] [-o DIR] [-r path/to/seed/] [-p] [-P] [-t DD:HH:MM:SS] [-i MAXITER] [-n MAXPROC] [-k] FILE`. If it errors instead, go to the rmg-install skill's known-errors table.

## 1. Run superminimal in a scratch directory (recommended)

The input is `examples/rmg/superminimal/input.py`:

- H2 + O2 at 1000 K and 1 bar.
- 5 kinetics families and `primaryThermoLibrary`.
- Terminates at 90% H2 conversion.

**Copy it out first.** RMG writes every output next to `input.py`, and a re-run in the same folder deletes the previous `pdep/`, `solver/` and `kinetics_database/`.

Conda/source:

```bash
JOB=/tmp/rmg_superminimal_$(date +%Y%m%d_%H%M%S)      # fresh dir; never reuse an old one
mkdir -p "$JOB" && cp "$RMG_PY/examples/rmg/superminimal/input.py" "$JOB/"
cd "$JOB" && python "$RMG_PY/rmg.py" -t 00:00:15:00 input.py > stdout.log 2>&1
tail -n 15 RMG.log
```

Docker. Put the job inside the mounted folder so the results are visible on the host:

```bash
mkdir -p /rmg/RMG-Py/myrmgfiles/superminimal
cp /rmg/RMG-Py/examples/rmg/superminimal/input.py /rmg/RMG-Py/myrmgfiles/superminimal/
cd /rmg/RMG-Py/myrmgfiles/superminimal && python /rmg/RMG-Py/rmg.py input.py
```

- `-t 00:00:15:00` is a safety wall time (`DD:HH:MM:SS`, lowercase `-t`).
- `-o DIR` sends output elsewhere. The directory must already exist.
- **Agents:** superminimal is quick enough to run in the foreground. Any longer job should run in the background with a wall time, with `RMG.log` monitored (see the rmg-run-job skill).
- **Running it in place** (`python rmg.py examples/rmg/superminimal/input.py`, as in the talk) works too. It fills the checkout's example folder with output, which `git status` will then show, and in Docker those files sit outside the mount.

## 2. What success looks like

The end of `RMG.log` (and stdout):

```
Performing final model checks...
No collision rate violators found in the model's core.

MODEL GENERATION COMPLETED

The final model core has 13 species and 19 reactions
The final model edge has 0 species and 0 reactions

RMG execution terminated at ...
```

Reference numbers from a run of this checkout (RMG-Py 3.3.0, conda, laptop-class CPU):

- About 18 s of wall time.
- "Memory used: ~1.2 GB".
- Final core of **13 species / 19 reactions**.
- Intermediate files `chemkin/chem0006.inp` … `chem0013.inp`.

Small differences after a database update are normal.

The top of `RMG.log` is worth showing the user. It contains:

- `Global RMG Settings: database.directory = ...`, which says which database was used and why.
- The `Version:` banner.
- `The current git HEAD for RMG-Py is:` and `...for RMG-database is:`, giving the commit hashes.

Warnings such as `Generate Output HTML option was turned on...` and `Edge species saving was turned on...` are expected: superminimal turns those options on.

| Ending | Meaning |
|---|---|
| `MODEL GENERATION COMPLETED` | Success |
| `MODEL GENERATION TERMINATED` + `not enough time ... wall time` | Hit `-t`. For superminimal this means something is badly wrong, e.g. a very slow first Julia compile. |
| Python traceback | Read the last frames. For install or import errors use the rmg-install skill. Otherwise follow the bug-report procedure in the rmg-contributing skill. |

## 3. Files produced (superminimal, all in the job directory)

| Path | What it is |
|---|---|
| `RMG.log` | Full log. A re-run moves the old one to `RMG_backup.log`, keeping only one backup. |
| `chemkin/chem.inp`, `chem_annotated.inp`, `species_dictionary.txt`, `tran.dat` | The final core mechanism in Chemkin format. The annotated file shows the source of each rate. The dictionary holds the adjacency lists that define each species. |
| `chemkin/chemNNNN.inp` | Snapshots after each core growth (NNNN = number of core species) |
| `chemkin/chem_edge*.inp`, `species_edge_dictionary.txt` | The edge, written only because `saveEdgeSpecies=True` |
| `cantera/chem.yaml`, `chem_annotated.yaml` | Cantera mechanism, written at the end of a completed run |
| `output.html`, `output_edge.html`, `species/*.png` | Browsable model report (`generateOutputHTML=True`) |
| `solver/simulation_1_<N>.csv/.png` | Reactor profiles per iteration (`saveSimulationProfiles=True`) |
| `seed/`, `restart_from_seed.py` | Seed mechanism, used to restart a run |
| `rms/chem<N>.rms` | RMS-format mechanism snapshots |
| `statistics.xls`, `plot/` | Execution statistics |
| `pdep/`, `kinetics_database/` | Empty here. They fill only with `pressureDependence()` or `-k`. |
| `collision_rate_violators.log` | Written only if some core reactions exceed the collision limit |

Next things to show the user:

- `output.html` in a browser.
- `chemkin/chem_annotated.inp` to see where each rate came from.
- To simulate the model, use the rmg-simulate-cantera or rmg-rms skill.

## 4. Makefile examples (`make eg0`, `make eg1`, ...)

These are defined in `RMG-Py/Makefile`. **Every `egN` target first runs `make all`**, which is the dependency check plus `pip install --no-build-isolation -e .`. That rebuilds RMG, and in a conda env where rmgpy wasn't pip-installed it **installs it**. Each target also wipes `RMG-Py/testing/egN/` before running. Ask the user before using them.

| Target | Runs | Output |
|---|---|---|
| `make eg0` | superminimal (H2 oxidation) | `testing/eg0/` |
| `make eg1` | minimal (ethane pyrolysis), with `coverage` and profiling (`-p`) | `testing/eg1/`, plus `htmlcov/` coverage in RMG-Py |
| `make eg3` | liquid_phase | `testing/eg3/` |
| `make eg6` | ethane-oxidation | `testing/eg6/` |
| `make eg8` | rms_constant_V (**needs Julia+RMS**) | `testing/eg8/` |

Also defined: `eg2` (1,3-hexadiene, needs MOPAC), `eg4` (thermoEstimator, QM), `eg5`, `eg7`, `eg9` and `eg10` (RMS).

## 5. Gotchas

- The first run on the **3.2.0** Docker image is very slow, because Julia compiles RMS (`domain.jl`) even for `--help`. Ignore the Julia warnings. In 3.3.0 Julia loads only when an RMS feature is used.
- Neither `python rmg.py` from the wrong directory nor a bare `rmg.py` works. Use `python $RMG_PY/rmg.py` (see rmg-install).
- Don't edit `examples/rmg/*/input.py` in place; copy it first.
- The `examples/rmg/superminimal/*.ipynb` notebooks are RMS demos and need Julia (`*_RMS.ipynb`).

## Next steps

- Write and run your own input, choose flags, and monitor long runs: **rmg-run-job**. The fully annotated template is `examples/rmg/commented/input.py`.
- Pick tolerances and a model-building strategy: **rmg-model-building-strategy**.
- Browse examples close to your chemistry in `examples/rmg/`: `minimal`, `ethane-oxidation`, `halogens`, `liquid_phase`, `minimal_surface`, `catalysis/`, and others.

When unsure, check:

- `RMG-Py/Makefile`
- `RMG-Py/rmgpy/util.py` (CLI flags)
- `RMG-Py/rmgpy/rmg/main.py` (log messages and outputs)
- `RMG-Py/documentation/source/users/rmg/running.rst` and `output.rst`
- `RMG-Py/examples/rmg/superminimal/input.py`
