---
name: rmg-advanced-settings
description: Tunes RMG-Py model-generation settings for speed, memory and species selection. Covers flux pruning (toleranceKeepInEdge, toleranceInterruptSimulation=1e8, maximumEdgeSpecies, minCoreSizeForPrune), filterReactions/filterThreshold, thermodynamic pruning, maxNumObjsPerIter/terminateAtMaxObjects, staging with repeated model()/simulator() blocks and maxNumSpecies, ranged reactors with nSims/balanceSpecies, the branching criterion, and the RMS-only criteria (transitory edge analysis, dead-end radical elimination, radical flux), plus the cost of diagnostic options. Use it when the user says "RMG runs out of memory", "the edge is huge", "RMG is too slow", "pruning isn't happening", "RMG misses chain branching / low-temperature chemistry", "NOx or another trace species is missing", "polymerization / molecular-weight growth model", "speed up RMG", or asks what an advanced model() option does.
---

# Advanced RMG model settings

Based on the 2025 RMG Workshop talk “Advanced RMG Model Settings” (Matt Johnson) and RMG-Py 3.3.0.

Prerequisites:
- Input-file basics and running jobs: `rmg-run-job`.
- Why species get missed and how to judge convergence: `rmg-model-building-strategy`.
- Copy-paste blocks, each checked against the docs/examples and parse-tested: [reference/recipes.md](reference/recipes.md).

**Rule zero.** Most "RMG missed species X" problems come from bad thermo or rate estimates, not the algorithm. Fix those first (`rmg-model-building-strategy`). Use the selection criteria below for the algorithmic failure modes.

## Where the time and memory go
| phase of the run | bottleneck | what helps |
|---|---|---|
| Early (small core) | Reaction generation (isomorphism checks), pdep master equations | `-n ~6` (about 2x, then saturates), `filterReactions`, species constraints, pdep `maximumAtoms` |
| Late (large core) | ODE simulation and species selection | RMS reactors (`rmg-rms`, about 2–3x), loosening tolerances, fewer reactors/`nSims` |
| Any time | **RAM is held by the edge** (edge ≫ core) | Pruning, `maximumEdgeSpecies`, filtering, constraints; thermo pruning as a last resort |

Where the switch between these regimes happens depends on the chemistry. Running out of RAM either crashes the run or makes it crawl. The docs say about 200k edge species fill 8 GB. Before you change settings, measure the edge size and memory in the log:
```bash
grep -E "The model edge has" RMG.log | tail -n 3; grep "Memory used" RMG.log | tail -n 1
```

## Symptom → setting
| symptom | first try | then |
|---|---|---|
| **Edge too big / out of memory** | `filterReactions=True`; flux pruning (recipe B) with `maximumEdgeSpecies` sized to RAM | Tighter `generatedSpeciesConstraints`; loosen `toleranceMoveToCore`; thermo pruning (recipe H) as the emergency option |
| **Too slow early** | `-n 6`; `filterReactions=True`; constraints (`maximumCarbonAtoms`, `maximumRadicalElectrons=2`) | pdep `maximumAtoms`; `maxNumObjsPerIter` 3–5 |
| **Too slow late** | Switch to an RMS reactor (`rmg-rms`) | Loosen the tolerance or use staging (recipe I); drop redundant reactors or lower `nSims` |
| **Pruning never happens** (`Attempting to prune...` absent) | `toleranceInterruptSimulation=1e8` and `toleranceKeepInEdge>0` | Make sure every reactor can reach its termination (time as well as conversion); core ≥ `minCoreSizeForPrune` |
| **`Attempted to prune a species that exceeded tol_move_to_core...`** | Raise `maximumEdgeSpecies` | Lower `minSpeciesExistIterationsForPrune` (back to ~2) |
| **Missing chain branching** (low-T combustion, QOOH → ketohydroperoxide → 2 OH) or **orphan radicals** (main path built, side paths missing, radicals too high) | Branching criterion (recipe D) | `maxNumObjsPerIter` around 5 (recipe C); lower `toleranceMoveToCore` |
| **Trace species missing** (NOx in methane combustion, a minor product) | Transitory edge analysis on that target (recipe E, RMS only; edge ≲ 300 species) | Old workaround: a contrived extra reactor with a high trace-species concentration, or force the expected species via `species()` |
| **MW growth / polymerization / Fischer–Tropsch**: diluted flux, radicals too high, missing chain transfer or termination | Dead-end radical elimination (recipe F, RMS only) | Branching criterion (helps somewhat); constraints to cap size |
| **High radical concentrations, termination products missing** | Radical flux criterion `toleranceRadMoveToCore` (recipe G, RMS only) | Branching criterion |
| **One condition converges slowly inside a range** | Add a fixed reactor at that condition alongside the ranged one | Raise `nSims` |
| **Catalytic or feedback species** (needs an intermediate two steps outside the core) | No numerical fix; keep lowering `toleranceMoveToCore` | Force the suspected species into the core |

## Settings in detail

### Filtering: `filterReactions=True`, `filterThreshold=1e8`
- Core species are not reacted together until their concentrations could produce a flux above `toleranceMoveToCore` × the characteristic rate, even at a maximal rate constant.
  - The bimolecular limit is `filterThreshold`, in m³/(mol·s). The trimolecular limit is that value / 1e3. The unimolecular limit is k_B T/h (`rmgpy/solver/simple.pyx`).
- The presenter: robust, so "always" use it in gas phase, and probably in liquid.
- In `liquidReactor`, `filterThreshold` is **ignored**; diffusion limits from the solvent viscosity are used instead (`solver/liquid.pyx`).
- On `surfaceReactor` it raises `NotImplementedError`.
- The docs say the default is 5e8; **the code default is 1e8**.

### Flux pruning: `toleranceKeepInEdge`, `toleranceInterruptSimulation`, `maximumEdgeSpecies`, `minCoreSizeForPrune=50`, `minSpeciesExistIterationsForPrune=2`
- An edge species whose flux ratio never exceeds `toleranceKeepInEdge` during the simulations is deleted. After that, the lowest-flux edge species are deleted until the edge is ≤ `maximumEdgeSpecies`.
- Set `toleranceKeepInEdge` to **about 0.1 × `toleranceMoveToCore`, and not more than that** (docs).
- Pruning runs **only after every reactor reaches its termination criterion without interruption**. That is why the interrupt tolerance must be very high (**1e8**): a simulation stopped early can't prove a species is unimportant later on.
- **`maximumEdgeSpecies` is not a hard cap.** It is enforced only by flux pruning (`toleranceKeepInEdge>0`) or thermo pruning (`main.py`, `model.py`). The default is 1,000,000. The talk said 100,000; that is wrong.
- Pruning together with pressure dependence: the talk was unsure whether it currently works well. The code removes networks that become empty. Check results when you combine them.

### Thermodynamic pruning: `toleranceThermoKeepSpeciesInEdge` (inf = off; 0.1–1 typical)
- Removes high-Gibbs-energy edge species immediately and always holds the edge at `maximumEdgeSpecies`. No completed simulation is needed.
- It is less safe than flux pruning; use it as an emergency option when memory is still out of control.

### Several objects per iteration: `maxNumObjsPerIter` (default 1), `terminateAtMaxObjects` (default False)
- RMG adds up to N species, reactions or networks per simulation, in the order they trip their criteria.
- This addresses the order dependence: adding B→C first can cut the apparent flux to B→D by about 10x.
- Use about 5, and not much more than 10.
- Raise `toleranceInterruptSimulation` somewhat above MoveToCore, so the simulation runs long enough to collect several objects.
- Use `terminateAtMaxObjects=True` when you are not pruning.
- Models get larger at a given tolerance, sometimes picking up chemistry that would otherwise be missed.

### Branching criterion: `toleranceBranchReactionToCore=0.001`, `branchingIndex=0.5`, `branchingRatioMax=1.0`
- Picks edge reactions by their expected effect on core-species concentrations, so it catches low-flux initiation, termination and chain-branching steps that the flux criterion misses.
- The recommended values above depend little on the system.
- The presenter called it the general-purpose option people should use more.
- It works with **native** reactors (`solver/base.pyx`).
- It produces larger models and later termination. Judge it by target convergence, not by whether the run terminates. On dodecane pyrolysis it improved agreement and found species that otherwise had to be added by hand.

### RMS-only criteria (Julia/RMS reactors such as `constantTPIdealGasReactor`; see `rmg-rms`)
- `toleranceTransitoryDict={'NO':0.2}`, `transitoryStepPeriod=20`: transitory sensitivity of a *target species* to edge reactions. Very powerful for trace species. Cost scales quadratically with core + edge size.
- `toleranceReactionToCoreDeadendRadical=0.01–0.1`: chain-transfer and termination selection for oligomer or MW-growth systems.
- `toleranceRadMoveToCore`: radical flux criterion.
- **With native reactors (`simpleReactor`, `liquidReactor`, `surfaceReactor`) these keywords are silently ignored.** They are passed only to the RMS simulate call (`rmgpy/rmg/reactionmechanismsimulator_reactors.py`). The talk didn't mention this restriction; `input.rst` does.

### Staging: repeat `model()` (and `simulator()`) blocks; `maxNumSpecies`
- Stages run in file order. A stage ends when it converges or reaches `maxNumSpecies` core species.
- Typical use: a coarse, cheap first stage, then tighter tolerances or extra criteria. Recipe I is based on `examples/rmg/minimal_staged`.
- Give the same number of `simulator()` blocks as `model()` blocks, or exactly one.
- Thermo-pruning setup and the initial `filterReactions` flag are read from the **first** `model()` block.

### Ranged reactors: `nSims`, `balanceSpecies`
- Give `temperature`, `pressure` and/or mole fractions as two-element lists. RMG samples `nSims` conditions per cycle with a weighted stochastic grid (not a regular grid).
- `nSims` should be at least 2+N, and as many as 2+5N, for N ranged dimensions.
- `balanceSpecies` (one non-ranged species, e.g. N2) keeps the other mole fractions within their ranges instead of renormalizing them.
- Supported by `simpleReactor`. `liquidReactor` supports T and concentration ranges. `surfaceReactor` supports T and P only. RMS reactors don't support ranges.
- Recipe J.

### Diagnostic options: cost vs value
| option | cost | use when |
|---|---|---|
| `saveEdgeSpecies=True` | **Slowest**: writes the whole edge (Chemkin + HTML) every iteration | Short debug runs: "is reaction X in the edge at all?" |
| `generateOutputHTML=True` | Slow; one PNG per species; can exhaust cluster inode quotas | On for small core models. With the edge, only for odd debugging |
| `saveSimulationProfiles=True` | Writes a CSV and PNG per simulation; not allowed with RMS reactors | Watching how an iteration evolves |
| `verboseComments=True` | Huge comments in the log and Chemkin files | Almost never: only to see how rate rules were averaged |
| `generatePlots=True` | Small | Statistics plots in `plot/` |
| `generateSeedEachIteration=True` | Cheap | Keep it on (needed for restarts) |

## Agent notes
- Size `maximumEdgeSpecies` and `-n` to the machine (`free -g`, `nproc`).
- Ask the user before settings that imply many hours or most of the RAM: tight tolerances, branching, transitory analysis on big systems.
- Make one change at a time, each in a new job directory. Compare targets between runs with the same `-t` (`rmg-run-job`).
- Don't treat "the run finished" as convergence. Show the user how the target predictions change with model size.

## When unsure
Sources of truth:
- `rmgpy/rmg/input.py` (`model()` defaults).
- `rmgpy/rmg/settings.py` (`ModelSettings`).
- `rmgpy/rmg/main.py`: the prune and stage loop.
- `rmgpy/solver/base.pyx`: flux, branching, interrupt and termination logic.
- `rmgpy/rmg/reactionmechanismsimulator_reactors.py`: RMS-only criteria.
- `documentation/source/users/rmg/input.rst` ("Advanced Setting" sections, "Staging").
- `examples/rmg/{pruning_test,propane_branching,nox_transitory_edge,minimal_staged,minimal_thermofilter,heptane-filterReactions}`.
