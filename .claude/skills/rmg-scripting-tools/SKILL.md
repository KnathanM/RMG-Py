---
name: rmg-scripting-tools
description: Runs RMG-Py's post-processing command-line scripts and Python API to analyze, compare and transform mechanisms. Covers generateChemkinHTML, diffModels, mergeModels, standardizeModelSpeciesNames, generateFluxDiagram, simulate, generateReactions, thermoEstimator, isotopes, checkModels, rmg2to3, and RMG-database's importChemkinLibrary and exportKineticsLibraryToChemkin, plus load_chemkin_file, load_species_dictionary, a minimal RMGDatabase load, load_rmg_py_job, and matching species between models by structure. Use when the user says "make the HTML for my model", "compare two models", "diff models", "merge mechanisms", "flux diagram", "estimate thermo for these species", "enumerate reactions", "load chem.inp in Python", "export a kinetics library to Chemkin", "import a Chemkin mechanism into RMG", "which species are the same in both models", or "No module named rmgpy when running a script".
---

# RMG scripting tools and Python API

Based on the 2025 RMG Workshop talk “Introduction to RMG Scripting Tools” and RMG-Py 3.3.0.

The talk's key point: running RMG is only the start. These tools help you ask "why?" and "what if?" about a model. The `.py` scripts are fill-in-the-arguments tools that are fine for long runs. The `ipython/` notebooks are interactive and use the API more deeply.

## 0. How to launch a script (read first)

See **rmg-install** to detect conda vs Docker and to find `$RMG_PY`.

```bash
# Docker or a pip-installed RMG: rmgpy is importable everywhere
python $RMG_PY/scripts/<tool>.py ARGS
# Source checkout where rmgpy is NOT pip-installed (e.g. this machine's rmg_env):
PYTHONPATH=$RMG_PY python $RMG_PY/scripts/<tool>.py ARGS
```

Without `PYTHONPATH`, `python scripts/x.py` fails with `ModuleNotFoundError: No module named 'rmgpy'`, even when run from inside `$RMG_PY`. Python puts the *script's* folder on `sys.path`, not the cwd. Activate the conda env, rather than calling its python by full path, so that `dot` and `ffmpeg` are on PATH for flux diagrams.

Most scripts write their output into the **current directory** or next to the input file. `cd` into a fresh folder first so you don't clobber the user's files.

## 1. Pick the tool

| Goal | Tool | Minimal command |
|---|---|---|
| Browse a model (species pictures, reactions, sources) | `generateChemkinHTML.py` | `... CHEMKIN DICT [OUTDIR]` → `output.html` |
| What changed between two models? | `diffModels.py` | `... chem1.inp dict1.txt chem2.inp dict2.txt [--diffOnly]` → `diff.html` |
| Combine mechanisms | `mergeModels.py` | `... --model1 chemA.inp dictA.txt --model2 chemB.inp dictB.txt` → `chem.inp`, `species_dictionary.txt` |
| Same names across models | `standardizeModelSpeciesNames.py` | `... --model1 ... --model2 ...` → `chem1.inp`, `chem2.inp`, ... |
| Flux-diagram movie | `generateFluxDiagram.py` | `... input.py chem_annotated.inp species_dictionary.txt` → `flux/1/*.png`, `flux_diagram.avi` |
| Re-simulate or get RMG-native sensitivity | `simulate.py` | `... input.py chem.inp species_dictionary.txt` → `solver/` |
| All reactions among given species (one step) | `generateReactions.py` | `... input.py` |
| Thermo for a list of species | `thermoEstimator.py` | `... thermo_input.py [-l]` → `chem_annotated.inp` |
| RMG library → Chemkin | `RMG-database/scripts/exportKineticsLibraryToChemkin.py` | `... LIBRARYNAME` |
| Chemkin → RMG libraries | `RMG-database/scripts/importChemkinLibrary.py` | `... chem.inp dict.txt NAME` (writes into the database) |

Full verified usage, outputs and caveats for every script are in `reference/scripts.md`. Runnable demos are in `examples/scripts/<tool>/run.sh` (diffModels uses `example.sh`). When a bash script prints nothing, it usually succeeded.

## 2. Gotchas (verified)

- **mergeModels: earlier models win.** If a species or reaction is already in `--model1`, the copy in `--model2` is discarded, including its thermo and kinetics. Put the model you trust most first.
- **Flux diagrams need exactly one condition.** If the input file's reactor uses ranges for T, P or composition, copy the input file and fix single values first. `fluxdiagram.simulate` calls `initialize_model(..., conditions=None)`. You also need Graphviz `dot` on PATH; otherwise you get `FileNotFoundError: "dot" not found in path`. Frames come first and the `.avi` is written at the end. Early frames look empty because the time steps start tiny.
- `simulate.py` only knows RMG's simple batch reactors, with no flow or geometry control. For real experiments, write Cantera code (**rmg-simulate-cantera**) or use RMS (**rmg-rms**).
- `diffModels` and `generateChemkinHTML` need the RMG **species dictionary**. A bare Chemkin file is not enough. For Chemkin from another source, add `-f/--foreign` where available.
- **Database-writing scripts:** `importChemkinLibrary.py`, `generateTree.py` and `machineWriteDatabase.py` write into `RMG-database/input/`. `machineWriteDatabase.py` has **no argument parsing**, so `--help` runs it and re-saves the whole database. Never run these to inspect usage. Ask the user, and check `git -C $RMG_DB status` is clean first.
- There is no `convertFAME` or `exportKineticsLibrary` script in RMG-Py. The import/export scripts are in **RMG-database/scripts/**.

## 3. Python API recipes (all tested on superminimal and minimal_surface output)

Run these from `$RMG_PY`, with `PYTHONPATH=$RMG_PY`, or in Docker.

```python
from rmgpy.chemkin import load_chemkin_file, load_species_dictionary, get_species_identifier
from rmgpy.species import Species

# Load a model -> (list[Species], list[Reaction])
spcs, rxns = load_chemkin_file("RUN/chemkin/chem_annotated.inp",
                               "RUN/chemkin/species_dictionary.txt",
                               "RUN/chemkin/tran.dat")            # transport optional
s = spcs[4]
print(s.label, s.index, get_species_identifier(s))   # 'H2' 1 'H2(1)': label has no suffix, the Chemkin name does
print(s.thermo.get_enthalpy(298.15) / 4184)           # kcal/mol
print(rxns[0], rxns[0].kinetics.get_rate_coefficient(1000.0))

# Surface model: gas file + surface_path
spcs, rxns = load_chemkin_file("RUN/chemkin/chem_annotated-gas.inp", "RUN/chemkin/species_dictionary.txt",
                               surface_path="RUN/chemkin/chem_annotated-surface.inp")

# Dictionary only: {chemkin_name: Species}
sd = load_species_dictionary("RUN/chemkin/species_dictionary.txt")

# Find a species BY STRUCTURE (labels and indices differ between runs)
oh = [x for x in spcs if x.is_isomorphic(Species().from_smiles("[OH]"))]

# Match species between two models by structure, not by label
spcs2, _ = load_chemkin_file("OTHER/chem_annotated.inp", "OTHER/species_dictionary.txt")
mapping = {}
for a in spcs:
    b = next((b for b in spcs2 if a.is_isomorphic(b)), None)
    if b is not None:
        mapping[get_species_identifier(a)] = get_species_identifier(b)
```

Minimal database load (thermo only, a few seconds):

```python
from rmgpy import settings
from rmgpy.data.rmg import RMGDatabase
db = RMGDatabase()
db.load(settings["database.directory"], thermo_libraries=["primaryThermoLibrary"],
        reaction_libraries=[], seed_mechanisms=[], kinetics_families="none",
        kinetics_depositories=[], depository=False, solvation=False)
# NB: in this version thermo is only loaded when surface=True, which is the default. Don't pass surface=False.
sp = Species().from_smiles("CCO"); sp.thermo = db.thermo.get_thermo_data(sp)
print(sp.thermo.get_enthalpy(298.15) / 4184, sp.thermo.comment)   # -57.88 kcal/mol, group additivity
```

Reload a finished job as an RMG object (input + model; loads the full database, so it's slow):

```python
from rmgpy.tools.loader import load_rmg_py_job
rmg = load_rmg_py_job("RUN/input.py", "RUN/chemkin/chem_annotated.inp",
                      "RUN/chemkin/species_dictionary.txt", generate_images=False)
core = rmg.reaction_model.core          # core.species, core.reactions; rmg.reaction_systems
```

Other modules in `rmgpy/tools/` worth knowing: `diffmodels`, `mergemodels`, `fluxdiagram`, `simulate`, `canteramodel` (see **rmg-simulate-cantera**), `uncertainty`, `ckcsvparser`, `isotopes`, `regression`. Relevant notebooks in `ipython/`: `generate_reactions.ipynb`, `mechanism_analyzer.ipynb`, `find_parameter_sources_and_assign_uncertainties.ipynb`, `kinetics_library_to_training.ipynb`, `local_uncertainty.ipynb`, `global_uncertainty.ipynb`.

## Agent notes

- Flux diagrams, `generateReactions`, `isotopes` (which runs a full RMG job) and `load_rmg_py_job` can take minutes or longer. Run them in the background.
- Write outputs in a new folder. Don't overwrite an existing `diff.html`, `chem.inp` or `flux/` without asking.
- Get confirmation before anything that writes to RMG-database. Point to **rmg-add-data** for the right way to add libraries.

**When unsure:** run `PYTHONPATH=$RMG_PY python $RMG_PY/scripts/<tool>.py --help` (except `machineWriteDatabase.py`), and read `rmgpy/tools/<module>.py`, `rmgpy/chemkin.pyx` (`load_chemkin_file`) and `rmgpy/data/rmg.py` (`RMGDatabase.load`).
