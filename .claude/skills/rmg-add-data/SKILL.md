---
name: rmg-add-data
description: Adds the user's own thermo and kinetics data to RMG. Covers writing thermo libraries (ThermoData/NASA/Wilhoit) and kinetics libraries (reactions.py + dictionary.txt with Arrhenius, MultiArrhenius, ThirdBody, Lindemann, Troe, PDepArrhenius, Chebyshev), choosing library vs training reactions, adding training reactions and refitting auto-generated (Blowers-Masel) trees, converting Chemkin files, using Arkane's RMG_libraries output, loading external libraries by path, and checking that RMG actually used the new data. Use when the user says "add my calculated thermo/rates to RMG", "make a thermo library", "make a kinetics library", "import a Chemkin mechanism", "add training reactions", "use my Arkane results in RMG", "custom library", "RMG ignored my library", or "refit the tree".
---

# Adding data to RMG (libraries, training reactions, trees)

Based on the 2025 RMG Workshop talk “Adding Data to RMG” and RMG-Py 3.3.0.

`$RMG_PY` and `$RMG_DB` are the RMG-Py and RMG-database checkouts. In Docker they are `/rmg/RMG-Py` and `/rmg/RMG-database`. See `rmg-install` to detect them. Background on how estimates are made is in `rmg-database`.

**Agent safety.** `$RMG_DB` is often shared, or is a git checkout the user cares about.
- Default to **external libraries** in the user's project folder (§4).
- Only write into `$RMG_DB` (or a copy of it) when the user agrees. Then tell them exactly which files changed (`git -C $RMG_DB status`).
- Every structure you write must be round-tripped first (`rmg-molecule-representation`). Do not invent adjlists from memory.

## 1. Decide where the data goes

| Situation | Put it in |
|---|---|
| Thermo for specific species (QM, Arkane, literature) | **Thermo library** (§2) |
| Many new species of one functional type, so better estimates are wanted for unseen molecules | Thermo **groups**. You must fit the group values yourself, e.g. with `RMG-database/scripts/fitThermoGroupsFromThermoLibrary.ipynb`. This is for advanced users. |
| A set of rates optimized together; rates that do not generalize; no family exists; or you are not confident in them | **Kinetics library** (§3) |
| Confident, generalizable rates that should improve estimates for similar reactions | **Training reactions** for the family (§5). Usually you build a library first, then convert it. |
| You want your rate to be used for exactly this reaction no matter what the trees say | A library or a seed. Libraries are searched before families. |

These rules come from `documentation/source/users/rmg/database/modification.rst`.

## 2. Thermo library

1. Copy [templates/thermo_library_template.py](templates/thermo_library_template.py). It has real entries in all three forms: `ThermoData` (Tdata/Cpdata/H298/S298), `NASA` (two `NASAPolynomial`s) and `Wilhoit`.
2. Rename the file. **The file name, without `.py`, is the library label RMG uses.** Keep `name =` the same.
3. Fill in the entries:
   - Give each a unique `index` and label.
   - `molecule` must be a full adjlist.
   - Units go in every tuple.
   - Put the provenance in `shortDesc`, which appears in `chem_annotated.inp` comments, and in `longDesc`.
4. Check that it loads (§7).

## 3. Kinetics library (a folder)

1. Copy the [templates/kinetics_library_template/](templates/kinetics_library_template/) folder (`reactions.py` + `dictionary.txt`). Every rate form is copied from a real database library.
2. **The folder name is the library label.** Keep `name =` the same.
3. Write `dictionary.txt`:
   - Blocks of `label` then adjlist, separated by blank lines.
   - Labels are case-sensitive and may not contain `+`. Example: `CH2(S)` with `u0 p1`.
4. Write `reactions.py` entries such as `label = "A + B <=> C + D"`. The loader enforces these rules (`rmgpy/data/kinetics/library.py`):
   - Every label must be in the dictionary.
   - The reaction must be balanced, with at most 3 reactants and 3 products.
   - `=>` requires `reversible=False`.
   - A specific collider `(+N2)` must appear on both sides and must be in the dictionary.
   - Duplicates need `duplicate=True`, or put them in one `MultiArrhenius`.
5. Write Troe, Lindemann and ThirdBody labels **without** `(+M)`.
   - Efficiency keys are SMILES matched to species by isomorphism.
   - Use the right structure: CO is `'[C-]#[O+]'`.
   - Some existing libraries use `'[C]=O'`, which is *triplet* CO and silently matches nothing.
6. Pressure-dependence flags (see `rmg-pressure-dependence`):
   - `elementary_high_p=True` means the entry, or the high-P limit of a Troe/Lindemann/PDep form, is a true elementary rate. RMG may then reuse it inside its own pdep networks.
   - `allow_pdep_route=True` also lets RMG add a pdep-network route between the same species.
   - `allow_max_rate_violation=True` is stored and saved, but nothing in RMG-Py 3.3.0 reads it. It is a database-side annotation that a rate exceeds the collision limit.
7. Units:
   - Bimolecular rates in `cm^3/(mol*s)` or `m^3/(mol*s)`.
   - Unimolecular rates in `s^-1`.
   - Termolecular rates and low-pressure limits in `cm^6/(mol^2*s)`.
   - Chebyshev needs `kunits` to match.
8. Library rates are used **as given**. They are *not* multiplied by degeneracy.

## 4. Use the library in a run

**External library (preferred, leaves `$RMG_DB` untouched).** Give the path in `database()`:
```python
database(
    thermoLibraries=['/abs/path/MyThermo.py', 'primaryThermoLibrary'],   # .py file path; order = priority
    reactionLibraries=['/abs/path/MyKinetics'],                          # folder holding reactions.py
    seedMechanisms=[],                                                   # or put the folder here to force into core
    ...)
```
- **Use absolute paths.** For kinetics, the path is tested relative to the *current working directory* first, before the database.
  - This means a folder in the cwd with the same name as a database library would shadow it.
  - The relative-name example is `examples/rmg/external_library/`.
- The label is the basename (`MyKinetics`). Do not reuse the name of a database library.

**Inside the database.** Copy the file to `$RMG_DB/input/thermo/libraries/MyThermo.py`, or the folder to `$RMG_DB/input/kinetics/libraries/MyKinetics/`. Then refer to it by name. Only do this with the user's consent, and tell them.

**A private database copy.** Copy RMG-database somewhere, then put an `rmgrc` file containing `database.directory: /path/to/copy/input` in the working directory, or in `~/.rmg/rmgrc`.
- Check the result: `python -c "from rmgpy import settings; print(settings['database.directory'], settings.sources['database.directory'])"`.
- Use this before running the database-writing scripts below, so they write into the copy.

## 5. Training reactions and trees

- Training data lives in `$RMG_DB/input/kinetics/families/<Family>/training/{reactions.py, dictionary.txt}`. It is like a library, except:
  - The dictionary adjlists carry the family recipe labels (`*1`, `*2`, `*3` ...) on the reacting atoms.
  - Each entry has a `rank` (1 is best, 10 is worst). Ranks are listed in `rmg-database` §4.
  - If a reaction is written in the reverse direction of the family, it must still use the template's atom labels.
- **Library to training (recommended route): `$RMG_PY/ipython/kinetics_library_to_training.ipynb`**, with `kinetics_library_to_training_tools.py`.
  1. Set `libraries=[...]` and `families=[...]`.
  2. Step 1 loads the database.
  3. Step 2a matches library reactions to the family and labels the atoms. It plots the old estimate against the library value.
  4. Step 2b is an optional interactive y/n review.
  5. Step 2c resolves multiple matches.
  6. Step 2d is the final review.
  7. Step 3 writes into the training files of `settings['database.directory']`.
  - It only adds a reaction when exactly one family matches.
  - It **modifies the database**, so use a private copy or get the user's OK.
  - It is interactive. Run it with the user in Jupyter rather than headless.
- What happens next depends on the family type. Check for `autoGenerated = True` in `groups.py` (see `rmg-database` §2):
  - **Hand-built family**, e.g. H_Abstraction, R_Addition_MultipleBond, intra_H_migration: new training reactions are turned into rules automatically the next time RMG loads the database (`add_rules_from_training`). Nothing else is needed.
  - **Auto-generated BM family** (44 families, e.g. R_Recombination, Disproportionation, Intra_R_Add_Endocyclic): **the tree must be refit**, or the new data does not change estimates. At most, the exact reaction picks up its training value.
    - Refit with `$RMG_DB/scripts/BM tree fitting notebook.ipynb`. The steps are `clean_tree` → `generate_tree` → `check_tree` → `regularize` → `get_reaction_matches` → `clean_tree_rules` → `make_bm_rules_from_template_rxn_map` → `cross_validate` → `family.save(...)`.
    - Or run `python $RMG_PY/scripts/generateTree.py FAMILY`. It only works for some families.
    - Both write into the database directory and can take a long time. **Ask before running them, use a database copy, and run them from a scratch cwd** (not from inside RMG-Py).
- To compare runs with and without training data, set `kineticsDepositories=['!training']`.
- The talk's advice: if the job is too hard, ask the RMG developers for help. They want contributed data. See `rmg-contributing` for pull requests.

## 6. Converting existing data

- **Chemkin + RMG species dictionary → libraries.** Use [templates/chemkin_to_library.py](templates/chemkin_to_library.py), which writes wherever you choose:
  ```bash
  python templates/chemkin_to_library.py chem.inp species_dictionary.txt MyMech /abs/out [--thermo therm.dat]
  # -> /abs/out/MyMech.py (thermo) and /abs/out/MyMech/{reactions.py,dictionary.txt}
  ```
  - It makes the same calls as `$RMG_DB/scripts/importChemkinLibrary.py CHEMKIN DICTIONARY NAME`. That official script **always writes into `settings['database.directory']`** (both `thermo/libraries/NAME.py` and `kinetics/libraries/NAME/`).
  - Either way you **need an RMG species dictionary** with an adjlist for every Chemkin name. A bare Chemkin file is not enough. Build one by round-tripping each species' SMILES (`rmg-molecule-representation`) and confirm the mapping with the user.
- **Arkane results.** Arkane writes `RMG_libraries/` into its output folder (see `arkane`).
  - In this version, a job with only thermo gives `RMG_libraries/thermo.py`.
  - A job with any kinetics or pdep gives `RMG_libraries/reactions.py` + `dictionary.txt`. The kinetics save **deletes the folder first**, so `thermo.py` is lost.
  - In the kinetics case, rebuild the thermo library from `output.py`, or run the thermo jobs separately.
  - Rename the outputs and use them as external libraries (§4).
- **RMG's own estimates as a library.** Use `python $RMG_PY/scripts/thermoEstimator.py input.py -l`, which writes `ThermoLibrary.py`.
- Other database scripts:
  - `$RMG_DB/scripts/exportKineticsLibraryToChemkin.py`
  - `fitThermoGroupsFromThermoLibrary.ipynb`
  - `AEC_procedure.ipynb` / `BAC_procedure.ipynb` (Arkane corrections)

## 7. Check that the files load (tested; run from a scratch dir)

```bash
python $RMG_PY/.claude/skills/rmg-add-data/templates/check_library.py /abs/MyThermo.py /abs/MyKinetics
#  Thermo library 'MyThermo': 3 entries
#       1 sBuOH   C4H10O  mult=1 H298= -295.01 kJ/mol ... SMILES=CCC(C)O
#  Kinetics library 'MyKinetics': 7 entries
#       5 H + O2 <=> HO2   Troe   k(1000 K, 1 bar) = 3.955e+04 (SI)
#  OK: all libraries loaded.
```
- The script uses RMG's own loader, so it raises the same errors RMG would: `Species X ... is missing from its dictionary`, `... was not balanced!`, adjlist errors, and so on.
- Check the printed formula, multiplicity and SMILES against what the user intended.
- Add `PYTHONPATH=$RMG_PY` if `rmgpy` does not import.

## 8. Check that RMG actually used the data

After a run:
```bash
grep -n "Loading kinetics library\|Loading thermodynamics library\|Adding reaction library\|seed mechanism" RMG.log
grep -n "Thermo library: MyThermo\|Library reaction: MyKinetics" chemkin/chem_annotated.inp | head
```
Tested: a superminimal run with external `MyThermo.py`/`MyKin` logged `Loading kinetics library MyKin from /…/MyKin...` and `Loading thermodynamics library from an external location: …`. `chem_annotated.inp` showed `! Library reaction: MyKin` and `! Thermo library: MyThermo`.

If your data is missing from the output:
- **Structure mismatch.** Libraries match by graph isomorphism. Round-trip the adjlist.
- **Spin.** The usual culprits are triplet vs singlet species and `[C]=O` used for CO.
- **Another library listed earlier won.** The first match wins.
- **A seed or another library has the same reaction.**
- **The reaction never involved core species.** Libraries only feed the edge, while seeds go straight into the core.
- **The species never formed.**

Gotchas:
- The docs say rate rules override training reactions. In 3.3.0, an **exact training match is used before rate rules** (`family.get_kinetics` checks depositories first; verified: source `Kinetics Depository H_Abstraction/training`).
- The docs refer to a `training.py` file. The real file is `training/reactions.py`.

When unsure, the source of truth is `rmgpy/data/kinetics/library.py` (load rules), `rmgpy/data/thermo.py` / `rmgpy/data/kinetics/database.py` (`load_libraries`, external paths), `rmgpy/rmg/main.py` (training/averaging at load), `documentation/source/users/rmg/database/modification.rst` and `input.rst` (External Libraries).
