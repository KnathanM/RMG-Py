# RMG input-file cheatsheet (RMG-Py 3.3.0)

Every keyword and default below comes from `rmgpy/rmg/input.py`. The function that implements each block is given in its heading. Keyword names are camelCase in the input file.

**How the file is executed:** with `__builtins__ = None` (`read_input_file`). You cannot use `import`, `float('inf')`, `int()`, `range()`, `len()` and so on. A builtin call fails with the unhelpful message `TypeError: 'NoneType' object is not subscriptable`. Only `True` and `False` are predefined.

**Required blocks:** `database`, at least one `species`, at least one reactor, `simulator`, `model`. Everything else is optional.

**Block order:** blocks run top to bottom. `species()` must come before any reactor that uses its label. `pressureDependence` may go anywhere after `database`.

---

## database() (`database`)
| keyword | default | notes |
|---|---|---|
| `thermoLibraries` | `[]` | First library wins. Example: `['BurkeH2O2','primaryThermoLibrary','thermo_DFT_CCSDTF12_BAC','DFT_QCI_thermo','CBS_QB3_1dHR']` |
| `reactionLibraries` | `[]` | Their reactions go into the **edge**. Write an entry as `'name'` or `('name', True)`. `True` appends the library's unused edge reactions to the Chemkin output |
| `seedMechanisms` | `[]` | Their reactions go straight into the **core** |
| `transportLibraries` | `None` | `None` loads **all** transport libraries. Example: `['PrimaryTransportLibrary']` |
| `frequenciesLibraries` | `[]` | Statmech libraries |
| `kineticsFamilies` | `'default'` | `'all'`, `'none'`, a list (`['H_Abstraction', ...]`), a named set from `RMG-database/input/kinetics/families/recommended.py` (`default`, `ch_pyrolysis`, `liquid_peroxide`, `surface`, `halogens`, `surface_development`, `electrochem`), or negations such as `['default', '!Intra_Disproportionation']` |
| `kineticsDepositories` | `'default'` → `['training']` | `'all'` or a list |
| `kineticsEstimator` | `'rate rules'` | This is the only option |
| `adsorptionGroups` | `'adsorptionPt111'` | Surface work only |

Library names are case-sensitive file and folder names under `RMG-database/input/{thermo,kinetics}/libraries/`. Use the `rmg-database` skill to choose libraries.

## species() (`species`)
`species(label, structure, reactive=True, cut=False, size_threshold=None)`
- `structure`: `SMILES("...")`, `InChI("...")`, `adjacencyList("""...""")`, `SMARTS("...")`, `fragment_adj(...)` or `fragment_SMILES(...)`. See `rmg-molecule-representation`.
- A label containing `+` raises `InputError`. A duplicate structure also raises `InputError`.
- Every listed species enters the core.
- **O2:** use `SMILES("[O][O]")`. Singlet `O=O` raises `ForbiddenStructureException` unless `allowSingletO2=True`.
- `reactive=False` makes the species inert to families. Library and seed reactions involving it are still used.
- RMG always adds Ar, He, Ne and N2 as non-reactive species (`main.py`), even if you don't list them.

## forbidden() (`forbidden`)
`forbidden(label, structure)` blocks a molecule (`SMILES`/`adjacencyList`) or a whole group (`adjacencyListGroup("""...""")`). Example: `examples/rmg/commented/input.py`.

## react() (`react`)
`react([('A','B'), ('C',)])` reacts only these tuples at the start. It is only used when `filterReactions=True`.

## simpleReactor() (`simple_reactor`)
An isothermal, isobaric, ideal-gas batch reactor.
| keyword | default | notes |
|---|---|---|
| `temperature` | required | `(1000,'K')`, or a range `[(800,'K'),(1400,'K')]` |
| `pressure` | required | `(1.0,'bar')`, or a range `[(1,'bar'),(10,'bar')]` |
| `initialMoleFractions` | required | `{'label': x}`, or a range `{'label': [x1, x2]}`. Normalized with a warning if the values don't sum to 1 (fixed values only) |
| `nSims` | 6 | Only used for ranged reactors. Forced to 1 otherwise |
| `terminationConversion` | None | `{'label': 0.9}`. The species needs a non-zero initial amount |
| `terminationTime` | None | `(1,'s')` |
| `terminationRateRatio` | None | e.g. `0.01`: current characteristic flux ÷ maximum characteristic flux so far |
| `balanceSpecies` | None | A single label, not a range. It absorbs the slack instead of normalizing |
| `sensitivity` | None | A list of labels, or `'all'`. Runs once after the model is complete. Writes `solver/sensitivity_*.csv` |
| `sensitivityThreshold` | 1e-3 | |
| `sensitivityTemperature`, `sensitivityPressure`, `sensitivityMoleFractions` | None | Required for sensitivity when the reactor is ranged |
| `constantSpecies` | None | Labels held at constant concentration |

At least one termination criterion is required (`InputError: No termination conditions specified`). The criteria are combined with OR.

## liquidReactor() (`liquid_reactor`)
`temperature`, `initialConcentrations={'label': (c,'mol/cm^3')}`, `terminationConversion`, `nSims=4`, `terminationTime`, `terminationRateRatio`, `sensitivity`, `sensitivityThreshold=1e-3`, `sensitivityTemperature`, `sensitivityConcentrations`, `constantSpecies`.
- This is the native RMG `LiquidReactor`, not an RMS reactor.
- It needs a `solvation(solvent='octane')` block. The solvent string is a database solvent name; see the website's solvent list.
- Temperature and concentrations may be ranges.
- Gas-phase runs reject solvent-specific libraries, and liquid runs reject libraries from a different solvent (`main.py check_libraries`).
- Example: `examples/rmg/liquid_phase`.

## solvation() (`solvation`)
`solvation(solvent, solventData=None)`. `solvent` must be a string.

## surfaceReactor() (`surface_reactor`)
Covered by the `rmg-catalysis` skill. In brief:
- Arguments: `temperature`, `initialPressure`, `initialGasMoleFractions`, `initialSurfaceCoverages`, `surfaceVolumeRatio`, `nSims=4`, plus termination.
- Needs `catalystProperties(metal='Pt111')`.
- Not supported: `filterReactions`, sensitivity, and composition ranges.

## RMS (Julia) reactors
These are `constantVIdealGasReactor`, `constantTPIdealGasReactor`, `liquidSurfaceReactor` and `constantTVLiquidReactor`. Covered by the `rmg-rms` skill.
- No T, P or composition ranges.
- No `sensitivity`.
- Incompatible with `saveSimulationProfiles=True`.
- Required for `toleranceTransitoryDict`, `toleranceReactionToCoreDeadendRadical` and `toleranceRadMoveToCore`.

## mbsampledReactor() (`mb_sampled_reactor`)
Molecular-beam sampled reactor: `temperature`, `pressure`, `initialMoleFractions`, `mbsamplingRate`, `terminationConversion`, `terminationTime`, `sensitivity`, `sensitivityThreshold`, `constantSpecies`. Rarely used.

## simulator() (`simulator`)
`simulator(atol, rtol, sens_atol=1e-6, sens_rtol=1e-4)`. `atol` and `rtol` are required.
- Typical values: `atol=1e-16, rtol=1e-8`.
- Repeat the block for staging, or give it once for all stages.

## model() (`model`)
| keyword | default | meaning |
|---|---|---|
| `toleranceMoveToCore` | **required** | Edge-species flux ÷ characteristic flux needed to enter the core. Typical 0.01–0.1 (docs) |
| `toleranceInterruptSimulation` | 1.0 | Must be ≥ MoveToCore. Set it equal to MoveToCore without pruning, or ~1e8 with pruning |
| `toleranceKeepInEdge` | 0.0 | > 0 enables flux pruning. Keep it ≤ 0.1 × MoveToCore |
| `maximumEdgeSpecies` | 1,000,000 | Edge cap, enforced by pruning |
| `minCoreSizeForPrune` | 50 | |
| `minSpeciesExistIterationsForPrune` | 2 | |
| `filterReactions` | False | Rate-based reaction filtering. Recommended for gas and liquid; not for surface |
| `filterThreshold` | 1e8 | The docs say 5e8; the code default is 1e8 |
| `maxNumSpecies` | None (inf) | Core size that ends the current stage |
| `maxNumObjsPerIter` | 1 | Objects added per simulation. A value ≤ 0 means unlimited |
| `terminateAtMaxObjects` | False | Stop the simulation once `maxNumObjsPerIter` objects are found |
| `toleranceThermoKeepSpeciesInEdge` | inf | Thermodynamic pruning (Gibbs criterion), typically 0.1–1 |
| `toleranceBranchReactionToCore` | 0.0 | Branching criterion. Recommended 0.001 |
| `branchingIndex` / `branchingRatioMax` | 0.5 / 1.0 | |
| `toleranceTransitoryDict` | `{}` | e.g. `{'NO':0.2}`. RMS reactors only |
| `transitoryStepPeriod` | 20 | Solver steps between transitory analyses |
| `toleranceReactionToCoreDeadendRadical` | 0.0 | 0.01–0.1. RMS reactors only |
| `toleranceRadMoveToCore` | inf | Radical-flux criterion. RMS reactors only |
| `toleranceMoveEdgeReactionToCore` (+`...Interrupt`) | inf | Dynamics criterion |
| `dynamicsTimeScale` | `(0.0,'sec')` | Earliest time the dynamics criterion may act |
| `ignoreOverallFluxCriterion` | False | Use MoveToCore only for pdep network exploration |
| `toleranceMoveEdgeReactionToSurface`, `toleranceMoveSurfaceSpeciesToCore`, `toleranceMoveSurfaceReactionToCore`, `toleranceMoveEdgeReactionToSurfaceInterrupt` | inf / None | Surface-algorithm tolerances |

Repeat `model()` (and `simulator()`) for staging; see the `rmg-advanced-settings` skill.

## pressureDependence() (`pressure_dependence`)
`pressureDependence(method, temperatures, pressures, maximumGrainSize=0.0, minimumNumberOfGrains=0, interpolation=None, maximumAtoms=None, completedNetworks=None)`
- `interpolation` must be given. Leaving it out crashes with `TypeError`.
- Reactor T and P must lie strictly inside the ranges.
- You need a `reactive=False` species in `initialMoleFractions`.
- Full details are in the `rmg-pressure-dependence` skill.

## generatedSpeciesConstraints() (`generated_species_constraints`)
Valid keys: `allowed`, `maximumCarbonAtoms`, `maximumOxygenAtoms`, `maximumNitrogenAtoms`, `maximumSiliconAtoms`, `maximumSulfurAtoms`, `maximumSurfaceSites`, `maximumSurfaceBondOrder`, `maximumHeavyAtoms`, `maximumRadicalElectrons`, `maximumSingletCarbenes`, `maximumCarbeneRadicals`, `allowSingletO2`, `speciesCuttingThreshold`.
- Any other key raises `InputError`. This includes `maximumIsotopicAtoms`, even though `input.rst` lists it.
- Defaults (`rmgpy/constraints.py`): atom, site and radical limits are unlimited; `maximumSingletCarbenes=1`; `maximumCarbeneRadicals=0`; `speciesCuttingThreshold=20`.
- **Always include** `allowed=['input species','seed mechanisms','reaction libraries']`. Without it, an input, seed or library species that breaks a constraint aborts with `ForbiddenStructureException`.
- Starting points: `maximumRadicalElectrons=2` (exceptions include the nitrogen triradical) and `maximumSurfaceSites=2`. Set atom caps from what you expect to form. Caps that are too tight cause truncation error.

## options() (`options`)
| keyword | default | notes |
|---|---|---|
| `name` | `'Seed'` | Name of the seed libraries |
| `generateSeedEachIteration` | True | Keep it True so you can restart |
| `saveSeedToDatabase` | False | True **writes into RMG-database**. Ask the user first |
| `units` | `'si'` | This is the only option |
| `generateOutputHTML` | False | `output.html` plus a `species/*.png` per species. Slow, and creates many files |
| `generatePlots` | False | Writes `plot/` statistics plots |
| `generatePESDiagrams` | False | Writes PDFs of pdep networks into `pdep/` |
| `saveSimulationProfiles` | False | Writes `solver/simulation_<rxn sys>_<n core spc>.csv` and `.png`. Errors with RMS reactors |
| `verboseComments` | False | Huge comments. Almost never useful |
| `saveEdgeSpecies` | False | Writes `chemkin/chem_edge*.inp` and `output_edge.html` each iteration. The slowest option |
| `keepIrreversible` | False | False makes library reactions reversible |
| `trimolecularProductReversible` | True | |
| `wallTime` | `'00:00:00:00'` | **Ignored when you run `rmg.py`**: the CLI `-t` default overwrites it. Use `-t` |
| `saveSeedModulus` | -1 | Save the seed every n iterations into `previous_seeds/` |
| `saveRestartPeriod` | — | Removed. Gives a warning only |

## uncertainty() (`uncertainty`)
`uncertainty(localAnalysis=False, globalAnalysis=False, uncorrelated=True, correlated=True, localNumber=10, globalNumber=5, terminationTime=None, pceRunTime=1800, pceErrorTol=None, pceMaxEvals=None, logx=True)`
- Runs after the model is complete.
- Needs `sensitivity=[...]` in a reactor.
- Global analysis needs the `muq` package; if it is missing, the global step is skipped with an error message.

## restartFromSeed() (`restart_from_seed`)
`restartFromSeed(path='seed')`, or the four explicit paths `coreSeed=`, `edgeSeed=`, `filters=`, `speciesMap=` (not both). Relative paths are resolved from the input file's directory. The `-r DIR` flag does the same thing.

## Rarely used
- `quantumMechanics(software, method, fileStore=None, scratchDirectory=None, onlyCyclics=False, maxRadicalNumber=0)`: legacy on-the-fly QM thermo (MOPAC/Gaussian). Group additivity is usually better now.
- `mlEstimator(...)`: chemprop-based thermo. The 3.3.0 code says support is "temporarily removed" (`rmgpy/ml/estimator.py`). Don't use it.
- `thermoCentralDatabase(...)` and `liquidVolumetricMassTransferCoefficientPowerLaw(...)`: specialist options.
- `catalystProperties(...)`: see `rmg-catalysis`.
