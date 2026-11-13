# RMG-Py 3.3.0 input file: starting template for a GAS-PHASE combustion / pyrolysis job.
# Edit every line marked  # EDIT.
#
# This file is executed with NO Python builtins: no imports, no float('inf'), no range().
# Use plain numbers, strings, lists, dicts and tuples only.
#
# Run (from a fresh job directory that holds only this file):
#   python $RMG_PY/rmg.py -t 00:02:00:00 input.py > stdout.log 2>&1 &
# Outputs are written next to this file (or to -o DIR).

# ----------------------------------------------------------------------------
# Data sources. Order matters: for every species or reaction, the FIRST library
# that contains it wins. Put the libraries you trust most first.
# ----------------------------------------------------------------------------
database(
    # Thermo libraries. Use the thermo that belongs to your seed mechanism
    # (BurkeH2O2 goes with the BurkeH2O2inN2 seed below).
    thermoLibraries=['BurkeH2O2', 'primaryThermoLibrary', 'thermo_DFT_CCSDTF12_BAC',
                     'DFT_QCI_thermo', 'CBS_QB3_1dHR'],
    # Reaction libraries go into the EDGE. RMG uses them only if their flux is large enough.
    reactionLibraries=[],
    # Seed mechanisms go straight into the CORE. For any oxidation job, seed the H2/O2
    # sub-mechanism. For PYROLYSIS (no O2), remove this oxidation seed.
    seedMechanisms=['BurkeH2O2inN2'],
    kineticsDepositories=['training'],
    kineticsFamilies='default',          # or a named set from RMG-database/input/kinetics/families/recommended.py
    kineticsEstimator='rate rules',      # the only option
)

# ----------------------------------------------------------------------------
# Species. Every species listed here goes into the core. Labels must not contain '+'.
# Listing the important species keeps their names and order the same across runs.
# ----------------------------------------------------------------------------
species(
    label='propane',                     # EDIT: your fuel
    reactive=True,
    structure=SMILES("CCC"),
)
species(
    label='O2',
    reactive=True,
    structure=SMILES("[O][O]"),          # triplet O2. SMILES "O=O" (singlet) raises an error
)
species(
    label='N2',
    reactive=False,                      # inert bath gas. Pressure dependence REQUIRES at least one
    structure=SMILES("N#N"),             # reactive=False species in initialMoleFractions
)

# ----------------------------------------------------------------------------
# Reactor(s). simpleReactor is an isothermal, isobaric batch reactor.
# Termination uses OR logic: the first criterion reached ends that simulation.
# Add more simpleReactor blocks to cover more conditions, or use ranges:
#   temperature=[(800,'K'),(1400,'K')], nSims=6   (ranged reactor; see SKILL.md)
# ----------------------------------------------------------------------------
simpleReactor(
    temperature=(1000, 'K'),             # EDIT. Must lie strictly inside pressureDependence temperatures
    pressure=(1.0, 'bar'),               # EDIT. Must lie strictly inside pressureDependence pressures
    initialMoleFractions={               # stoichiometric propane/air. Values are normalized if they do not sum to 1
        'propane': 0.0403,
        'O2': 0.2016,
        'N2': 0.7581,
    },
    terminationConversion={'propane': 0.9},   # Keep it reachable. If equilibrium caps conversion, the job never converges
    terminationTime=(1.0, 's'),              # Safety net. Always pair a conversion target with a time
)

# ----------------------------------------------------------------------------
# ODE solver tolerances. These are rarely the cause of problems.
# ----------------------------------------------------------------------------
simulator(
    atol=1e-16,
    rtol=1e-8,
)

# ----------------------------------------------------------------------------
# Model enlargement. toleranceMoveToCore is REQUIRED and is relative to the
# characteristic flux. Start loose (0.1), then tighten (0.05, 0.02, 0.01) until your
# target predictions stop changing.
# ----------------------------------------------------------------------------
model(
    toleranceMoveToCore=0.1,
    toleranceInterruptSimulation=0.1,    # equal to MoveToCore when NOT pruning
    filterReactions=True,                # recommended for gas phase (not available for surface reactors)
    # To prune the edge (saves memory on big jobs), use these instead:
    # toleranceInterruptSimulation=1e8,
    # toleranceKeepInEdge=0.01,          # at most ~0.1 x toleranceMoveToCore
    # maximumEdgeSpecies=200000,         # ~200k edge species fill about 8 GB RAM
    # minCoreSizeForPrune=50,
    # minSpeciesExistIterationsForPrune=2,
)

# ----------------------------------------------------------------------------
# Pressure dependence. This is OFF unless this block is present. Keep it for almost all
# gas-phase work (combustion, pyrolysis, low-P or high-P experiments).
# The reactor T and P must lie STRICTLY inside these ranges.
# ----------------------------------------------------------------------------
pressureDependence(
    method='modified strong collision',  # robust, fast. Recommended for RMG runs
    maximumGrainSize=(0.5, 'kcal/mol'),
    minimumNumberOfGrains=250,
    temperatures=(300, 2200, 'K', 10),   # (Tmin, Tmax, units, number of T points)
    pressures=(0.01, 100, 'bar', 10),    # (Pmin, Pmax, units, number of P points)
    interpolation=('Chebyshev', 6, 4),   # REQUIRED. Basis counts must be < number of T and P points.
                                         # Or ('PDepArrhenius',) for PLOG output
    maximumAtoms=15,                     # skip pdep for adducts with more than 15 atoms (limits cost)
)

# ----------------------------------------------------------------------------
# Species constraints. ALWAYS keep the 'allowed' line, otherwise any input, seed or
# library species that breaks a constraint aborts the run.
# ----------------------------------------------------------------------------
generatedSpeciesConstraints(
    allowed=['input species', 'seed mechanisms', 'reaction libraries'],
    maximumCarbonAtoms=6,                # EDIT: a bit larger than your fuel
    maximumOxygenAtoms=5,                # EDIT
    maximumRadicalElectrons=2,
)

# ----------------------------------------------------------------------------
# Output options. Diagnostics slow RMG down. Keep saveEdgeSpecies and
# verboseComments False except when debugging.
# ----------------------------------------------------------------------------
options(
    units='si',
    generateSeedEachIteration=True,      # needed to restart a crashed or timed-out run
    generateOutputHTML=False,            # True draws a PNG per core species. Fine for small models
    generatePlots=False,
    saveSimulationProfiles=False,        # True writes solver/simulation_*.csv each iteration (not with RMS reactors)
    saveEdgeSpecies=False,               # slowest option. Writes the whole edge every iteration
    verboseComments=False,
    generatePESDiagrams=False,           # True draws a PDF per pdep network into pdep/
)
