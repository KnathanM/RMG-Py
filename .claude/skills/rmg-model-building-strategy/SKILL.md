---
name: rmg-model-building-strategy
description: Guides the iterative workflow for building an accurate kinetic model with RMG. The loop is build, simulate, run sensitivity/uncertainty analysis, improve the key thermo and kinetics (QM/Arkane, libraries), rebuild, and repeat until the model stops changing. Covers which questions to ask before starting, a first-iteration review checklist, converging prediction targets rather than tolerances, error types and magnitudes, fixing thermo before kinetics, and the rules for fitting to data. Use it when the user asks "how do I build a good mechanism", "my RMG model doesn't match experiment", "what should I check in my RMG output", "which parameters should I calculate", "is my model converged", "should I tune rates to fit data", "RMG gives weird species / very fast rates", or plans a modeling project with RMG.
---

# RMG model-building strategy

Based on the 2025 RMG Workshop talk “RMG Suggestions” (building good mechanisms with RMG) and RMG-Py 3.3.0.

This skill covers judgment and workflow. For the mechanics, see:
- Writing and running jobs: `rmg-run-job`.
- Settings for species selection: `rmg-advanced-settings`.
- Pressure dependence: `rmg-pressure-dependence`.
- Simulation, sensitivity and uncertainty tools: `rmg-simulate-cantera`, `rmg-scripting-tools`, `rmg-rms`.
- Better parameters: `arkane`, `rmg-add-data`, `rmg-database`.

One RMG run almost never gives quantitative accuracy. Plan for several rebuild cycles from the start.

## 1. Before you start: ask the user
Write the answers down; they decide every later choice.
1. **Prediction targets.** Which outputs matter: ignition delay, product selectivity, conversion vs time, a trace species (NOx), a fouling precursor? At what conditions?
2. **Required accuracy.** Factor of 2? 20%? Qualitative trends only?
3. **Conditions to cover.** T, P and composition ranges. Phase: gas, liquid (which solvent) or surface. The real application may be far from the lab experiments; the model's value lies in extrapolating to it.
4. **Known chemistry.** Expected products, intermediates and time scales. Get these from the literature or colleagues, not from LLM summaries.
   - Are there trusted mechanisms or libraries for the small-molecule core (e.g. an H2/O2 or C0–C2 seed)?
   - Elements present?
5. **Validation data.** Which experiments are available, and what reactor were they run in (shock tube, RCM, JSR, flow reactor, batch)? You need the reactor details to simulate them correctly.
6. **Budget.** CPU time per RMG run, RAM, and whether QM calculations (ARC/Arkane) are possible.

## 2. The iteration loop
```
RMG database + chemical knowledge + conditions
      │
      ▼
  1. Build with RMG ──► 2. Simulate the target experiments (right reactor model!)
      ▲                      │
      │                      ▼
  5. Put the improved  ◄── 3. Sensitivity + uncertainty analysis; compare with experiment
     values into the          │
     database (thermo/        ▼
     kinetics libraries,  4. Improve the few key parameters:
     training reactions)     QM via ARC/Arkane, literature values, new families
      │
      └──► REBUILD with RMG (go to 1). Repeat until the model stops changing.
```
- **Always rebuild after fixing parameters.** Corrected thermo or rates change which species and reactions RMG selects. Patching the Chemkin file instead leaves truncation error from the old, wrong parameters.
- "Stops changing" means two things: the target predictions are stable between iterations, and the sensitive reactions and species stay the same.
  - Compare consecutive mechanisms with `scripts/diffModels.py`. When rmgpy isn't pip-installed, set `PYTHONPATH=$RMG_PY`. Run it in a scratch directory: it writes `diff.html`, `species1/` and `species2/` into the current directory.
- Mechanism simulation and analysis matter most. If you understand the mechanism's pathways, branchings and rate-limiting steps, you can guess which parameters are wrong. Use flux diagrams (`scripts/generateFluxDiagram.py`), sensitivities, and `ipython/mechanism_analyzer.ipynb`.

## 3. Iteration stages and what to focus on
**First iteration: get a sane model. It doesn't need to be accurate yet.**
- Use loose tolerances, e.g. `toleranceMoveToCore=0.1`, filtering on, pdep on for gas phase.
- List the important species in the input file and include the appropriate seed mechanisms (with their matching thermo).
- Then run the review checklist in section 4.

**Intermediate iterations: improve the sensitive parameters.**
- Bring in values from calculations (Arkane) and the literature for the sensitive and uncertain parameters.
  - **Thermo first**, then kinetics where appropriate. On surfaces, people often calculate both together.
- Try different seed mechanisms and libraries.
- Force species you suspect are missing by listing them in `input.py`. In the next iteration, check that they are actually *used* (have flux); otherwise they were not missing.
- Converge **selectivities first**, then time scales and conversion.

**Late iterations: quantitative refinement.**
- Focus on the key branching points and pathways.
- Look for reactions that are *not* sensitive now but would be if their (uncertain) values were somewhat different. Uncertainty analysis finds these; sensitivity alone does not.
- Look for chemistry RMG doesn't know about: missing families, poorly estimated reactions you never calculated.

## 4. First-iteration review checklist
Go through these items with the user after each early build.
- [ ] Read the **first 30–50 core species** in the order they were added: `grep "^Adding species .* to model core" RMG.log`, or the `SPECIES` block of `chemkin/chem_annotated.inp`, which is in core order. Map labels to structures with `chemkin/species_dictionary.txt`. Do they match the expected chemistry?
- [ ] **Weird or unexpectedly important species**: strange rings, carbenes, high-energy radicals or long chains entering early. These almost always mean bad thermo. Check each one's thermo source in `chem_annotated.inp` (group additivity vs library) and compare with a better estimate.
- [ ] **Very fast rate coefficients**, especially reverse rates driven by bad thermo.
- [ ] **`collision_rate_violators.log`** (written at completion only if violators exist). Treat every entry as a probable thermo or estimate error.
- [ ] **Expected reactions that are missing.** They may need a library entry, a new reaction family, or a change in how the species is represented (resonance, multiplicity).
- [ ] **Pressure dependence on** (gas phase), with a sensible inert bath gas.
- [ ] **Truncation from settings.** Species constraints too tight? Was the run stopped by `-t`/`-i` before the targets converged?
- [ ] **Reactor model.** Does the RMG reactor resemble the experiment? Conditions too far from the real reactor cause *internal* reactor error in species selection.

## 5. Converge targets, not tolerances
- RMG's `toleranceMoveToCore` and termination criteria have **no physical meaning**. Getting a run to "finish" at 0.01 doesn't mean fluxes are resolved to 1%.
- Build at several tolerances, e.g. 0.1 → 0.05 → 0.02 → 0.01. Simulate the targets with each model, and stop when the targets stop changing as the model grows.
- A run that never "completes" can still be converged for your targets. A run that completed can still be unconverged.
- Use the same `-t` wall time for runs you compare.
- If tightening the tolerance alone doesn't pick up the chemistry you need, see `rmg-advanced-settings`. It covers the branching criterion, taking several species per iteration (`maxNumObjsPerIter`), transitory edge analysis for trace targets, and dead-end radical elimination for molecular-weight growth.

## 6. Error types and how big they are
| error | source | how to reduce |
|---|---|---|
| **Parameter error** | Wrong thermo or rate values | QM (ARC/Arkane), literature, libraries. Highest-sensitivity × uncertainty first |
| **Truncation: internal parameter / internal reactor error** | Bad parameters or reactor conditions inside RMG cause wrong species selection | Shrinks as parameters and reactor setup improve, which is why you fix these first |
| **Truncation: missing species or reaction** | RMG doesn't know the chemistry (no family or library) | New family or library reactions, a different species representation; found through literature and QM |
| **Truncation: species-selection error** | The algorithm misses low-flux but important paths (feedback loops, "orphan radicals", low-T chain branching, MW growth) | `rmg-advanced-settings`; force species into the core |
| **Reactor error** | The simulated reactor differs from the experiment | Model the real reactor. Example: rapid compression machines need the compression stroke simulated for reactive fuels. Test extra complexity and check how others model the apparatus |

Typical magnitudes quoted in the talk (not independently verified):
- RMG H-abstraction estimates (rate rules/SIDT, 1000 K): median error factor about 4; 2σ about 3 orders of magnitude. Expect worse for chemistry unlike the training data.
- Gas-phase group-additivity thermo: 2σ about 8 kcal/mol, similar to B3LYP. Good modern QM reaches about 1 kcal/mol. Liquid is somewhat worse because of solvation; surfaces are much worse.
- **Errors depend on temperature.** An energy error ΔE gives a factor of exp(ΔE/RT). 1 kcal/mol is about a factor of 5 at 300 K but about 1.5 at 1000 K, so low-temperature predictions need better energies.
- Most rate coefficients only need to be within about 3 orders of magnitude. A significant minority need about a factor of 10. A handful need to be as accurate as possible.
- **Thermo matters more than kinetics.** It sets the equilibrium constants, the reverse rates and the shape of the potential energy surface.

## 7. Symptom → likely cause → action
| symptom | likely cause | action |
|---|---|---|
| Strange species enter the core early | Bad thermo (group additivity outside its training set) | Check the thermo source; add a thermo library entry or calculate it (`arkane`, `rmg-add-data`); rebuild |
| Entries in `collision_rate_violators.log` | Bad thermo (reverse) or bad rate estimate | Fix the thermo, or add a library rate; rebuild |
| An expected product never appears | Missing family or library reaction, or species-selection error | Check the edge (`saveEdgeSpecies=True` in a short debug run). If it is absent, add chemistry; if it is in the edge, see `rmg-advanced-settings` or force the species into the core |
| Right products, wrong time scale | Parameter error in the rate-limiting or chain-branching steps; reactor error | Sensitivity analysis → calculate the top parameters. Check the reactor model |
| Model agrees at high T, fails at low T | Energy errors amplified at low T; low-T chain branching missed | Better energies for the sensitive steps; branching criterion |
| Predictions keep changing as the tolerance tightens | Not converged | Keep tightening (with pruning/filtering), or use advanced selection settings |
| Large models but targets unchanged | Already converged | Stop and use the smaller model |
| Simulation disagrees with an experiment run at low P | Pressure dependence off, or a measured rate at low P compared with a high-P rate | Turn on `pressureDependence` (`rmg-pressure-dependence`) |
| Radical concentrations look too high | Missing consumption pathways (orphan radicals, MW growth) | Branching or dead-end-radical criteria (`rmg-advanced-settings`) |

## 8. Fitting to experimental data (avoid it)
- Don't tune parameters to make plots go through data points. The value of a detailed model is extrapolation, and fitting destroys the experiment's independence as an accuracy check. The RMG adage is "farther from the data, closer to the truth".
- It is fine if predictions miss some points, as long as you can explain where the error comes from (reactor, parameters, truncation).
- **If the user insists:**
  - Adjust only **1–3 parameters**: those with the largest (sensitivity × uncertainty) for the target.
  - Keep them physically reasonable, e.g. below the collision limit.
  - **Disclose exactly what was changed** in the main text, not buried in the SI.
  - Never fit all parameters to the data.

## 9. Agent notes
- Each rebuild is a new job directory, e.g. `v1_tol0.1`, `v2_tol0.05`, `v3_newthermo`. Never overwrite earlier iterations; they are needed for comparison.
- Before adding entries to the shared RMG-database (libraries, training reactions), tell the user. Prefer a separate library they can version.
- Ask before launching long or high-memory builds. Record the tolerance, libraries, RMG-Py and RMG-database commits (from the `RMG.log` header) and the wall time of each iteration.

## When unsure
Sources of truth:
- `documentation/source/users/rmg/input.rst`: model tolerances and advanced settings.
- `rmgpy/rmg/main.py` and `rmgpy/solver/base.pyx`: what RMG actually does.
- `scripts/diffModels.py` and `scripts/generateFluxDiagram.py`.
- `ipython/local_uncertainty.ipynb`, `ipython/global_uncertainty.ipynb` and `ipython/mechanism_analyzer.ipynb`.
The quantitative error figures above are from the workshop talk and have not been verified against the code.
