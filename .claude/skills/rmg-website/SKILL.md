---
name: rmg-website
description: Guides use of the RMG website (rmg.mit.edu) tools and their local equivalents. The site offers molecule search and drawing, thermo search by SMILES/adjacency list/name/InChI/CAS, kinetics search, a database browser, solvation tools, a pressure-dependent network explorer, and Chemkin visualize/compare/merge/flux/populate-reactions/plot-kinetics/NASA tools. Includes tested local scripts that estimate thermo for a SMILES and family kinetics for reactants, and maps each web tool to an RMG-Py script. Use when the user says "look it up on the RMG website", "what does RMG estimate for the thermo of X", "search kinetics for A + B", "draw this adjacency list", "compare two models", "merge mechanisms", "visualize my chem.inp", "flux diagram", or "which libraries have this species".
---

# RMG website (rmg.mit.edu) and local equivalents

Based on the 2025 RMG Workshop talk “RMG Website” and RMG-Py 3.3.0.

**Prefer the local equivalents.**
- The website runs a **newer RMG-Py and RMG-database than this checkout**. Its `/version` page showed 2026 commits, while this checkout is 3.3.0. Its numbers can therefore differ from what the user's own RMG runs will produce.
- Local tools use the user's database and libraries. They can be scripted and the results reproduced.
- Use the website (WebFetch, or tell the user to open it) for quick visual checks, or when there is no local install.
- To detect how RMG is installed locally (conda or Docker, `$RMG_PY`, `$RMG_DB`), see `rmg-install`.
- Run local scripts from a scratch directory, not from inside RMG-Py.

## 1. Tool map

| Website (https://rmg.mit.edu/...) | What it does | Local equivalent |
|---|---|---|
| `/molecule_search` | Takes an adjlist, SMILES, name, InChI, InChIKey or CAS (some species only). Press **Tab** to resolve the identifier, then "Draw Molecule". Shows the adjlist, SMILES and other names. Has buttons for "Generate Resonance Structures", "Search thermochemistry" and transport (Joback LJ) | `rmg-molecule-representation/templates/check_structure.py` (adjlist, SMILES, resonance); `templates/estimate_thermo.py` (thermo) |
| `/database/thermo/molecule/<URL-encoded adjlist>` | Thermo results page for one structure. Every library hit plus the group-additivity estimate, with Cp/H/S/G plots and NASA output. **This is a plain GET, so it works with WebFetch.** | `templates/estimate_thermo.py --all SMILES` |
| `/database/kinetics/search/` | Kinetics for 1 reactant, 2 reactants, or reactants + products. Shows library and rate-rule results with k(T) plots. It is a POST form, so use a browser. Logged-in users get "Create training rate from average". | `templates/estimate_kinetics.py FAMILY SMILES [SMILES]`; `scripts/generateReactions.py input.py` (all families) |
| `/database/` | Browses thermo, kinetics, solvation, statmech and transport libraries, groups, families (with schematics), training sets and depositories | `ls $RMG_DB/input/...` (see `rmg-database` §2) and reading the files |
| `/database/solvation/search/` | Solvent search, Abraham solute parameters, ΔG/ΔH/ΔS of solvation at 298 K, T-dependent ΔG_solv, Henry's law/VLE, solid solubility | `ipython/estimate_solvation_thermo_and_search_available_solvents.ipynb`, `ipython/temperature_dependent_solvation_free_energy.ipynb` (solid solubility has no local equivalent here) |
| `/pdep/` | Upload an Arkane or pdep network input to see the network and PES | Run `Arkane.py` on the network file. It writes `network.pdf` (see `arkane`, `rmg-pressure-dependence`) |
| `/tools/chemkin` | Visualize a Chemkin file plus a species dictionary | `python $RMG_PY/scripts/generateChemkinHTML.py CHEMKIN DICTIONARY [OUTPUT_DIR] [-f]` |
| `/tools/compare` | Compare two models | `python $RMG_PY/scripts/diffModels.py CHEMKIN1 DICT1 CHEMKIN2 DICT2 [--thermo1 F] [--thermo2 F] [--web] [--diffOnly] [--commonDiffOnly]` |
| `/tools/merge_models` | Merge two models | `python $RMG_PY/scripts/mergeModels.py --model1 chem1.inp dict1.txt [tran1.dat] --model2 chem2.inp dict2.txt ...` (up to `--model5`; earlier models take priority) |
| `/tools/flux` | Flux-diagram video | `python $RMG_PY/scripts/generateFluxDiagram.py INPUT CHEMKIN DICTIONARY [CHEMKIN_OUTPUT] ...` |
| `/tools/populate_reactions` | All reactions among a set of species | `python $RMG_PY/scripts/generateReactions.py input.py` |
| `/tools/plot_kinetics` | Plot forward and reverse k from Chemkin-format reactions and a dictionary | `rmgpy.chemkin.load_chemkin_file` plus `rxn.get_rate_coefficient(T, P)` |
| `/tools/evaluate_nasa` | Human-readable H/S/Cp from a Chemkin NASA polynomial | `load_chemkin_file(chem, dict)` then `spc.thermo.get_enthalpy(T)` and so on |
| `/tools/group_draw` | Draw a group adjlist. **This was broken at the 2025 workshop.** | `Group().from_adjacency_list(s)`, then `mol.is_subgraph_isomorphic(group)` tests (`rmg-molecule-representation` §3) |
| `/resources` | Publications and past workshop videos | none |
| Profile (log in) | Preferred units and theme | none |

Script details and examples are in the `rmg-scripting-tools` skill. Runnable examples live in `examples/scripts/*/run.sh`.

## 2. Thermo for a species, locally (tested)

```bash
cd /tmp/scratch     # any scratch dir
python $RMG_PY/.claude/skills/rmg-website/templates/estimate_thermo.py "CCO" "C[CH2]"
#  CCO  formula=C2H6O  multiplicity=1
#    H298 = -236.07 kJ/mol   S298 = 279.38 J/mol/K ...
#    source: Thermo library: DFT_QCI_thermo
python $RMG_PY/.claude/skills/rmg-website/templates/estimate_thermo.py --all "CC=O"   # every library + GAV, like the website
```
- Prefix with `PYTHONPATH=$RMG_PY` if `import rmgpy` fails. In Docker, `$RMG_PY` is `/rmg/RMG-Py`.
- Edit `LIBRARIES` at the top of the script to match the user's `thermoLibraries`. The order is priority.
- It takes about 10 s with two libraries and about 30 s with `--all`.

Alternative: `python $RMG_PY/scripts/thermoEstimator.py input.py [-l]`.
- The input needs a `database(thermoLibraries=[...])` block plus `species(label=..., structure=SMILES(...))` entries.
- It writes `chem_annotated.inp` and `species_dictionary.txt`, with NASA polynomials and source comments.
- `-l` also writes `ThermoLibrary.py`, a ready-made RMG thermo library.
- See `examples/scripts/thermoEstimator/input.py`.

## 3. Kinetics for reactants, locally (tested)

```bash
python $RMG_PY/.claude/skills/rmg-website/templates/estimate_kinetics.py H_Abstraction CCC "[OH]"
#  [OH] + CCC <=> O + C[CH]C  | source: Kinetics Depository H_Abstraction/training
#  [OH] + CCC <=> O + [CH2]CC | source: rate rules   ("Estimated using template ... Euclidian distance = 1.0")
python $RMG_PY/.claude/skills/rmg-website/templates/estimate_kinetics.py Disproportionation "CC[CH]C" "CC(C)[O]"
```
- Run it for **one family at a time**, which takes about 15 s.
- It uses the same `family.get_kinetics(...)` call as RMG. It then calls `fix_barrier_height()`, which converts Blowers-Masel rules to Arrhenius using ΔH_rxn.
- It does not search reaction libraries.
- To see every reaction RMG would generate across all families, use `generateReactions.py` on a small input file instead.

## 4. Using the website from the agent

- **Thermo by adjlist** (GET):
  1. Build the adjlist with `check_structure.py`.
  2. URL-encode it: `python -c "import urllib.parse,sys;print(urllib.parse.quote(open(sys.argv[1]).read().strip(), safe=''))" adj.txt`.
  3. Fetch `https://rmg.mit.edu/database/thermo/molecule/<encoded>`.
  4. In the results, each library hit is a "Result #N – <library>" block and the last block is "Group additivity".
- Kinetics search, molecule search and the tools are **POST forms**. Give the user the URL and the exact inputs, rather than trying to submit them.
- **SMILES traps also apply on the site.** `OO` is hydrogen peroxide. O2 is `[O][O]`. A bare `O` is water. Always click "Draw Molecule" and check the structure (`rmg-molecule-representation`).
- Website kinetics are elementary, non-catalytic gas-phase estimates.
- The site's database is newer than the local one, so cite which source you used.

## Gotchas

- The talk said: always draw the molecule before trusting a search result. Name and CAS lookups go through external resolvers and only work for some species.
- `/tools/group_draw` (draw a functional group) was broken in 2025. Use local `Group` tests instead.
- Kinetics families with new rules may show no schematic image on the site. That is cosmetic.
- Do not upload unpublished or proprietary mechanisms to the public website without the user's consent. Use the local scripts instead.

When unsure, the source of truth is the local scripts in `$RMG_PY/scripts/` (run each with `-h`), `rmgpy/data/thermo.py` and `rmgpy/data/kinetics/family.py`, and the live site (https://rmg.mit.edu, `/version` for its backend commits).
