# model() recipes (RMG-Py 3.3.0)

Each block below was checked against `documentation/source/users/rmg/input.rst` or `examples/rmg/*/input.py`, and parses with `rmgpy/rmg/input.py`. Tolerances are relative to the characteristic flux. Treat the numbers as starting points and converge your targets (see `rmg-model-building-strategy`).

## A. Plain first build (no pruning)
Source: `input.rst` "Model Tolerances" and "Filtering".
```python
model(
    toleranceMoveToCore=0.1,
    toleranceInterruptSimulation=0.1,   # equal to MoveToCore: stop and add as soon as something qualifies
    filterReactions=True,               # gas/liquid only
)
```

## B. Flux pruning (memory-limited runs)
Source: `input.rst` "Speed Up by Pruning". Add `filterReactions=True` as well, as in `examples/rmg/pruning_test`.
```python
model(
    toleranceMoveToCore=0.5,
    toleranceInterruptSimulation=1e8,   # never interrupt, so simulations finish and pruning can run
    toleranceKeepInEdge=0.05,           # at most 10% of MoveToCore
    maximumEdgeSpecies=200000,          # ~200k edge species is about 8 GB RAM. Scale to the machine
    minCoreSizeForPrune=50,
    minSpeciesExistIterationsForPrune=2,
    filterReactions=True,
)
```
Pruning runs only when **all** reactors reached a termination criterion without being interrupted in that iteration, `toleranceKeepInEdge > 0`, and the core has at least `minCoreSizeForPrune` species (`main.py`). Look for `Attempting to prune...` in `RMG.log`.

With the interrupt tolerance at 1e8, every iteration runs each simulation to termination and adds all the species that crossed MoveToCore along the way. Iterations take longer, but more is added per iteration.

## C. Several objects per iteration
Source: `input.rst` "Taking Multiple Species At A Time". The talk suggested about 5, and no more than about 10.
```python
model(
    toleranceKeepInEdge=0.0,
    toleranceMoveToCore=0.1,
    toleranceInterruptSimulation=0.3,   # somewhat above MoveToCore, so the simulation can collect several
    maxNumObjsPerIter=5,
    terminateAtMaxObjects=True,         # recommended when not pruning
)
```

## D. Branching criterion (chain branching, low-T combustion, orphan radicals)
Source: `input.rst` "Branching Criterion" and `examples/rmg/propane_branching`. It works with native reactors (`base.pyx`).
```python
model(
    toleranceMoveToCore=0.3,
    toleranceInterruptSimulation=0.3,
    maxNumObjsPerIter=1,
    terminateAtMaxObjects=True,
    filterReactions=True,
    toleranceBranchReactionToCore=0.001,  # the recommended values; they depend little on the system
    branchingIndex=0.5,
    branchingRatioMax=1.0,
)
```
Expect larger final models. Judge convergence by your targets, not by whether the run terminates.

## E. Transitory edge analysis for a trace target (e.g. NO). RMS reactor required
Source: `examples/rmg/nox_transitory_edge`. Needs Julia/RMS (`rmg-rms`).
```python
constantTPIdealGasReactor(temperature=(900,'K'), pressure=(10.0,'bar'),
    initialMoleFractions={"N2": 4, "O2": 1, "ethane": 2.0/7.0},   # the target ("NO") must be a defined species
    terminationConversion={'ethane': .90}, terminationTime=(40,'s'))
model(
    toleranceMoveToCore=0.3,
    toleranceInterruptSimulation=0.3,
    maxNumObjsPerIter=1,
    terminateAtMaxObjects=True,
    filterReactions=False,                # as in the example
    toleranceTransitoryDict={'NO': 0.2},  # species label -> tolerance
    transitoryStepPeriod=20,              # solver steps between analyses. Raise it to cut cost
)
```
Cost grows quadratically with core + edge size. The talk's rule of thumb: it slows badly once the edge is beyond roughly 300 species. The target needs some pathway that produces it.

## F. Dead-end radical elimination (polymerization, oligomer, MW growth). RMS reactor required
Source: `input.rst` "Deadend Radical Elimination".
```python
model(
    toleranceMoveToCore=0.01,
    toleranceReactionToCoreDeadendRadical=0.01,   # 0.01-0.1
)
```

## G. Radical flux criterion (high radical concentrations, missing terminations). RMS reactor required
Source: `input.rst` "Radical Flux Criterion".
```python
model(
    toleranceMoveToCore=0.1,
    toleranceRadMoveToCore=0.2,
)
```

## H. Thermodynamic pruning (emergency memory cap)
Source: `input.rst` "Thermodynamic Pruning" and `examples/rmg/minimal_thermofilter`.
```python
model(
    toleranceMoveToCore=0.5,
    toleranceInterruptSimulation=0.5,
    toleranceThermoKeepSpeciesInEdge=0.5,   # 0.1-1. Smaller removes more
    maximumEdgeSpecies=200000,
    minCoreSizeForPrune=50,
)
```
Criterion: (G − Gmax,core) / (Gmax,core − Gmin,core), evaluated at the highest reactor T. Species are removed immediately, and the edge cap is always maintained. It is less safe than flux pruning: at tight tolerances it can drop species RMG would have added.

## I. Staging (cheap coarse stage, then a finer stage)
Source: `examples/rmg/minimal_staged`, `input.rst` "Staging".
```python
simulator(atol=1e-16, rtol=1e-8)      # stage 1
simulator(atol=1e-16, rtol=1e-8)      # stage 2 (or give only ONE simulator block for all stages)
model(toleranceKeepInEdge=0.0, toleranceMoveToCore=1.0, toleranceInterruptSimulation=1.0,
      maximumEdgeSpecies=100000, maxNumObjsPerIter=1, maxNumSpecies=10)    # stage 1 ends at 10 core species
model(toleranceKeepInEdge=0.0, toleranceMoveToCore=0.1, toleranceInterruptSimulation=1.0,
      maximumEdgeSpecies=100000, maxNumObjsPerIter=3, maxNumSpecies=100)   # stage 2 (the last stage) ends the run
```
- A stage ends when it converges or reaches `maxNumSpecies` (`The maximum number of species (N) has been hit, Exiting stage K`).
- Give either the same number of `simulator()` blocks as `model()` blocks, or one `simulator()` block for all stages.
- Thermo-pruning setup and `filterReactions` initialization read the **first** `model()` block (`main.py`). Keep those options consistent across stages.

## J. Ranged reactor (cover a condition range with one system)
Source: `input.rst` "Range Based Reactors" and `examples/rmg/pruning_test`. Native reactors only.
```python
simpleReactor(
    temperature=[(1000,'K'),(1500,'K')],
    pressure=[(1.0,'bar'),(10.0,'bar')],
    nSims=12,                                  # at least 2+N, up to 2+5N, for N ranged dimensions (here N=3)
    initialMoleFractions={"ethane": [0.05,0.15], "O2": 0.1, "N2": 0.9},
    balanceSpecies="N2",                       # N2 absorbs the slack. The sum of range widths must be <= x(N2)
    terminationConversion={'ethane': 0.1},
    terminationTime=(1e1,'s'),
)
```
- Conditions are drawn by weighted stochastic grid sampling, which favors conditions that recently returned objects.
- Convergence is guaranteed only at the last `nSims` conditions. If one condition converges slowly, add a fixed reactor at it.
