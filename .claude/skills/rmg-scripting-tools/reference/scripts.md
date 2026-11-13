# RMG command-line scripts: verified usage (RMG-Py 3.3.0)

Usage was checked against each script's argparse (`--help`) in this checkout. "cwd" means the directory you run the script from.
All scripts need `rmgpy` importable. In a source checkout where rmgpy is not pip-installed, prefix them with `PYTHONPATH=$RMG_PY` (see SKILL.md).

## RMG-Py/scripts/

| Script | Usage | Writes | Notes |
|---|---|---|---|
| `generateChemkinHTML.py` | `CHEMKIN DICTIONARY [OUTPUT_DIR] [-f/--foreign]` | `output.html` + `species/` in OUTPUT_DIR (default cwd) | Same HTML that `options(generateOutputHTML=True)` makes. `-f` for Chemkin files not made by RMG. Example dir is misspelled `examples/scripts/generateChemkimHTML/` |
| `diffModels.py` | `CHEMKIN1 SPECIESDICT1 CHEMKIN2 SPECIESDICT2 [--thermo1 F] [--thermo2 F] [--diffOnly] [--commonDiffOnly] [--web]` | `diff.html` + `species1/`, `species2/` in cwd | Matches species by structure. Thermo and kinetics comparisons: blue = identical, green = similar, red = different. Unique species and reactions are listed at the bottom. Example: `examples/scripts/diffModels/example.sh` (not `run.sh`) |
| `mergeModels.py` | `--model1 CHEM DICT [TRAN] --model2 CHEM DICT [TRAN] [... --model5]` | `chem.inp`, `species_dictionary.txt` (+ `tran.dat` if any transport given) in cwd | **Earlier models win.** A species or reaction already in model 1 is dropped from later models. List the model you trust most first |
| `standardizeModelSpeciesNames.py` | `--model1 CHEM DICT [TRAN] ... [--model5]` | `chem1.inp`, `species_dictionary1.txt`, `chem2.inp`, ... in cwd | Gives the same species the same name in every model |
| `generateFluxDiagram.py` | `INPUT CHEMKIN DICTIONARY [CHEMKIN_OUTPUT] [-s SPECIES_DIR] [-f] [--no-dlim] [-n MAXNODE] [-e MAXEDGE] [-c CONCTOL] [-r RATETOL] [-t TSTEP] [--centralSpecies i,j] [--rad R] [--centralReactionCount N] [--super] [--saveStates] [--readStates] [--java]` | `<INPUT dir>/flux/<reactor#>/flux_diagram_NNNN.{dot,png}` + `flux_diagram.avi` (6 fps) | **One condition only.** Fix every range in the input's reactor (T, P, composition) before running. Needs Graphviz `dot` and `ffmpeg` on PATH (both come with rmg_env, so activate the env). Takes minutes. `--centralSpecies` takes species *indices* |
| `simulate.py` | `INPUT CHEMKIN DICTIONARY [--no-dlim] [-f]` | `<INPUT dir>/solver/simulation_*.csv/png`, `sensitivity_*_SPC_*.csv` + `_reactions.png`/`_thermo.png`, `simulate.log` | Uses the reactors in INPUT (RMG's simple batch reactors only). Runs sensitivity if `sensitivity=[...]` is set, and uncertainty if an `uncertainty()` block exists. Example: `examples/scripts/simulate/sensitivity/` |
| `generateReactions.py` | Same CLI as `rmg.py`: `FILE [-o DIR] [-q/-v/-d] [-r SEED] [-p] [-P] [-t DD:HH:MM:SS] [-i MAXITER] [-n MAXPROC] [-k]` | A normal RMG output tree (`chemkin/`, `output.html`, ...) next to FILE | Runs a single reaction-enumeration step for all input species; it does not iterate like a full RMG run. Example: `examples/scripts/generateReactions/` |
| `thermoEstimator.py` | `INPUT [-l/--library]` | `chem_annotated.inp` (NASA polynomials, group or library comments) + `species_dictionary.txt` next to INPUT. `-l` also writes `ThermoLibrary.py` | INPUT is a thermo-only input file: `database(thermoLibraries=[...])`, `species(...)`, and optionally `solvation`, `quantumMechanics`, `mlEstimator`, `catalystProperties`. The docstring's "output.txt" is stale. Examples: `examples/scripts/thermoEstimator/input.py`, `input_QM.py`, `input_ml.py` |
| `isotopes.py` | `input [--output DIR] [--original MECH_DIR] [--maximumIsotopicAtoms N] [--useOriginalReactions] [--kineticIsotopeEffect simple]` | Isotope-labelled model in `--output` | Takes an RMG input file. Without `--original` it first runs a full RMG job (in `<output>/rmg/`); with `--original RUN` it reuses that run's chemkin files |
| `checkModels.py` | `NAME BENCHCHEMKIN BENCHSPECIESDICT TESTEDCHEMKIN TESTEDSPECIESDICT` | Log of differences | Used by the regression tests |
| `generateTree.py` | `FAMILYNAME` | **Overwrites** `RMG-database/input/kinetics/families/<FAMILY>/` | Rebuilds a family tree from training data. Only works for some families. Creates `treegen.log` in the cwd even for `--help`. Database-developer tool: ask the user before running |
| `machineWriteDatabase.py` | **No arguments. Any argument, `--help` included, is ignored and the script runs** | **Re-saves every family and group in the RMG-database directory** | Database-developer tool. Never run it to "see the usage". Ask the user first, and make sure RMG-database is a clean git tree |
| `rmg2to3.py` | `filename... (-0 \| -1 \| -2) [-w] [-n] [-x] [-y] [-z] [-a]` | With `-w`, edits files in place (keeps backups unless `-n`) | Migrates user code from RMG-Py 2.x to 3.x names. Without `-w` it only reports |

## RMG-database/scripts/

| Script | Usage | Writes | Notes |
|---|---|---|---|
| `exportKineticsLibraryToChemkin.py` | `LIBRARYNAME` (e.g. `BurkeH2O2inN2`) | `chem.inp` + `species_dictionary.txt` in cwd | RMG library format → Chemkin |
| `importChemkinLibrary.py` | `CHEMKIN DICTIONARY NAME` | **Into the database:** `input/thermo/libraries/NAME.py` and `input/kinetics/libraries/NAME/{reactions.py,dictionary.txt}` | Chemkin → RMG libraries. Changes the shared database; see **rmg-add-data** and confirm with the user |

Other analysis scripts are on contributors' forks and branches, such as the presenter's comparative flux diagram branch. None of them are in this checkout.

## examples/scripts/ (runnable demos)

`diffModels/` (`example.sh`), `generateChemkimHTML/`, `generateFluxDiagram/`, `generateReactions/`, `mergeModels/`, `simulate/sensitivity/`, `simulate/withoutSensitivity/`, `standardizeModelSpeciesNames/`, `thermoEstimator/` (`run.sh`, `run_QM.sh`, `run_ml.sh`).
Each `run.sh` calls `python ../../../scripts/<tool>.py ...` (four levels up for `simulate/*`), so it only works in place inside the checkout. When it runs, it writes its output into the examples tree.
