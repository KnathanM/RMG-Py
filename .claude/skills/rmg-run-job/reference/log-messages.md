# RMG.log messages: what each means and what to do (RMG-Py 3.3.0)

The messages come from `rmgpy/rmg/main.py`, `rmgpy/solver/base.pyx`, `rmgpy/rmg/model.py`, `rmgpy/rmg/pdep.py` and `rmgpy/rmg/input.py`. `RMG.log` sits in the output directory. If a previous `RMG.log` was there, it was moved to `RMG_backup.log`, which keeps only one backup.

## Quick monitoring commands
```bash
LOG=path/to/job/RMG.log
tail -n 30 $LOG                                          # what is happening now
grep -E "The model (core|edge) has" $LOG | tail -n 2     # current core and edge size
grep -E "Execution time|Memory used" $LOG | tail -n 2    # wall time and RAM so far
grep -c "Conducting simulation" $LOG                      # roughly, how many reactor simulations so far
grep -E "exceeded the minimum rate for moving to model core" $LOG | tail -n 5   # what is entering the core
grep -nE "MODEL GENERATION (COMPLETED|TERMINATED)|Traceback|Error|error" $LOG | tail
grep -nE "WARNING" $LOG | sort | uniq -c | sort -rn | head    # recurring warnings
```
`statistics.xls` in the output directory tracks core and edge size, memory and time per iteration.

## Start-up (input and database)
| message | meaning | action |
|---|---|---|
| `Reading input file "..."` followed by a copy of the input | Parsing started | — |
| `The input file "..." was invalid:` + traceback | Syntax, name or type error in input.py | Fix the line shown. `TypeError: 'NoneType' object is not subscriptable` usually means a builtin (`float`, `int`, `range`) was used; the input file has no builtins |
| `InputError: You must provide a toleranceMoveToCore value` | `model()` is missing it | Add it |
| `InputError: toleranceMoveToCore must be less than or equal to toleranceInterruptSimulation` | The interrupt tolerance is below MoveToCore (its default is 1.0) | Raise `toleranceInterruptSimulation` |
| `InputError: No termination conditions specified for reaction system #N` | The reactor has no termination | Add `terminationTime` and/or conversion |
| `InputError: Invalid generated species constraint 'X'` | Unknown key, e.g. `maximumIsotopicAtoms` | Remove or rename it (see the cheatsheet) |
| `InputError: Species X is a duplicate of Y` | Two `species()` blocks have the same structure | Remove one |
| `species ... label cannot include a + sign` | Bad label | Rename it |
| `Initial mole fractions do not sum to one; normalizing.` | Warning only | Fine, unless you meant different values |
| `AssertionError: Reaction system T is above/below pressure_dependence range` (or `P`) | Reactor T or P is not strictly inside the `pressureDependence` range | Widen `temperatures`/`pressures` |
| `AssertionError: Pressure Dependence calculations require at least one inert (nonreacting) species for the bath gas.` | No `reactive=False` species in `initialMoleFractions` | Add N2 or Ar with `reactive=False` and give it a mole fraction |
| `Interpolation model must be set to either 'Chebyshev' or 'PDepArrhenius'` | Bad `interpolation` | Fix it |
| `ForbiddenStructureException: Species constraints forbids input species X` / `Input species X is globally forbidden` | A constraint or forbidden structure hits an input species | Add `allowed=['input species','seed mechanisms','reaction libraries']` |
| `... RMG expects the triplet form of oxygen ...` | `O=O` was used | Use `SMILES("[O][O]")` |
| `DatabaseError: Thermo/Kinetics library 'X' was obtained in 'S' solvent ...` | Solvent library used in a gas run, or the solvent doesn't match | Remove the library or fix `solvation()` |
| `Invalid input for user defined maximum number of processes` | `-n` is larger than the CPU count | Lower `-n` |
| `Invalid format for wall time` | `-t` is not `DD:HH:MM:SS` | Use four fields, e.g. `00:04:00:00` |

## Each iteration
| message | meaning | action |
|---|---|---|
| `Beginning model generation stage N...` | A new `model()` stage started | — |
| `Conducting simulation of reaction system N...` | Simulating reactor N (ranged reactors repeat this `nSims` times) | — |
| `At time T s, species S at rate ratio R exceeded the minimum rate for moving to model core of X` | S will be added to the core | Normal. Check S is chemically sensible; strange species usually point to bad thermo |
| `... exceeded the minimum rate for simulation interruption of X` + `terminating simulation due to interrupt...` | The simulation stopped early to enlarge the model | Normal. Pruning cannot happen in this iteration |
| `At time T s, PDepNetwork #N at R exceeded the minimum rate for exploring of X` | A pdep network will be expanded | Normal when pdep is on |
| `At time T s, Reaction ... at a branching number of ... exceeded ...` | Branching criterion fired | Normal with `toleranceBranchReactionToCore` |
| `Reached max number of objects...preparing to terminate` | `maxNumObjsPerIter` was hit | Normal |
| `At time T s, reached target termination time.` / `... conversion: X of S` / `... RateRatio: R` | This reactor simulation finished without interruption | Pruning can run once **all** reactors reach this |
| `The model core has N species and M reactions` / `The model edge has ...` | Current sizes | Watch the edge size against RAM |
| `Execution time (DD:HH:MM:SS): ...` / `Memory used: ... MB` | Progress | Compare memory against available RAM |
| `Attempting to prune...` then `Pruning N species whose rate ratios ... did not exceed ...` | Flux pruning ran | — |
| `Attempted to prune a species that exceeded tol_move_to_core, pruning settings for this run are likely bad` | `maximumEdgeSpecies` is too small for this chemistry | Raise `maximumEdgeSpecies` or lower `minSpeciesExistIterationsForPrune` |
| `Reached maximum number of edge species` + `...Thermodynamic filtering` | Thermo pruning is active | — |
| `Making seed mechanism...` | `seed/` was updated (restart point) | — |
| `The maximum number of species (N) has been hit, Exiting stage K ...` | `maxNumSpecies` ended a stage | Normal for staging |

## Solver problems
| message | meaning | action |
|---|---|---|
| `Trying to step from time ... resulted in a solver (DASPK) error` then `Resurrecting Model...` and `... was added to model core in model resurrection process` | The ODE solve failed; RMG added the highest-flux edge object and carried on | Usually harmless if rare. If it repeats, suspect bad thermo or rates; check the species added |
| `Model Resurrection has failed` + `ValueError: invalid_objects could not be filled during resurrection process` | Fatal ODE failure | Check thermo and rates of recent core species. Try tighter `simulator()` tolerances. Restart from the seed after fixing |
| `species S was added to model core to avoid singularity` | Zero characteristic flux | Normal at the very start |

## Pressure dependence
| message | meaning | action |
|---|---|---|
| `Updating PDepNetwork #N` / `Calculating phenomenological rate coefficients for ...` | A master equation is being solved | Many of these early on is normal and slow |
| `Exploring isomer X in pressure-dependent network #N` | The network grew | — |
| `k(T,P) for net reaction ... exceeds high-P k(T) by F at T K, P bar` | k(T,P) is above k∞ (grain discretization error or bad inputs) | If F is large and the reaction matters, try more grains (`minimumNumberOfGrains`) or inspect `pdep/networkN_*.py` |
| `Network N has been drawn and saved as networkN_M.pdf ... to aid debugging` + `InvalidMicrocanonicalRateError` | The master equation failed | Inspect the PDF and the `pdep/` file; usually a badly estimated energy or rate. See `rmg-pressure-dependence` |
| `PressureDependenceError: Path reaction ... with no high-pressure-limit kinetics` | A library reaction without usable k∞ ended up in a network | See `elementary_high_p` in `rmg-pressure-dependence` |
| `NetworkError: Unknown method "..."` | Typo in `method` (raised only when the first network is solved) | Use `'modified strong collision'`, `'reservoir state'` or `'chemically-significant eigenvalues'` |
| `No unreactive species to identify as bath gas` | No inert in the core | Add a `reactive=False` species |
| `Network reaction ... matched an existing core/edge reaction ... from the X library, and was not added` | The library reaction wins over the network estimate | Expected. See `allow_pdep_route` |

## End of run
| message | meaning | what exists |
|---|---|---|
| `MODEL GENERATION COMPLETED` + `The final model core has N species and M reactions` | Normal finish | Everything, including `cantera/chem.yaml`, the collision-violator check and sensitivity/uncertainty output |
| `MODEL GENERATION TERMINATED` + `There is not enough time to complete the next iteration before the wall time is reached.` | `-t` wall time (stops early when the next iteration is predicted to overrun) | `chemkin/` and `seed/` only. No `cantera/` and no final checks. Restart, or convert with `python -m cantera.ck2yaml --input=chemkin/chem_annotated.inp --transport=chemkin/tran.dat --output=chem.yaml --permissive` |
| `MODEL GENERATION TERMINATED` + `The maximum number of iterations of N has been reached` | `-i` limit | As above |
| `No collision rate violators found in the model's core.` | Clean | — |
| `N CORE reactions violate the collision rate limit! See the 'collision_rate_violators.log'` | Some core k exceed the collision limit | Read `collision_rate_violators.log`. Usually bad thermo (reverse rates) or bad estimates |
| `CoreError: Although the model has completed, species X is isomorphic to species Y in the core` | Duplicate core species (a bug) | Report it on GitHub with the adjacency lists printed |
| `Could not generate Cantera files ...` | Chemkin to YAML conversion failed | Run `python -m cantera.ck2yaml --input=chemkin/chem_annotated.inp --transport=chemkin/tran.dat --output=chem.yaml --permissive` and read its error |
| Log ends with a traceback and no "MODEL GENERATION" line | Crash | Read the traceback. The `seed/` from the last iteration can be used to restart |
| Log stops growing, process gone, no traceback | Usually killed for running out of memory (check `dmesg`/scheduler logs) | Reduce memory use: pruning, `maximumEdgeSpecies`, `filterReactions`, constraints (`rmg-advanced-settings`) |
