# RMG-Py 3.3.0 input template: gas + surface (heterogeneous catalysis), native surfaceReactor.
# Adapted from examples/rmg/minimal_surface and examples/rmg/catalysis/ch4_o2.
# Edit everything marked EDIT. Labels used in surfaceReactor must match species() labels.

database(
    # Put surfaceThermoPt111 FIRST: adsorbate thermo is computed for Pt(111) and then
    # shifted to your metal by linear scaling of the binding energies.
    thermoLibraries=['surfaceThermoPt111', 'primaryThermoLibrary', 'thermo_DFT_CCSDTF12_BAC', 'DFT_QCI_thermo'],
    # EDIT: a surface kinetics library that matches your chemistry/metal (see RMG-database/input/kinetics/libraries/Surface/)
    reactionLibraries=[('Surface/CPOX_Pt/Deutschmann2006_adjusted', False)],
    seedMechanisms=[],
    kineticsDepositories=['training'],
    kineticsFamilies=['surface', 'default'],   # 'surface' = family set in kinetics/families/recommended.py
    kineticsEstimator='rate rules',
    # adsorptionGroups='adsorptionPt111',      # default; also adsorptionNi111, adsorptionLi
)

# EDIT: EITHER a metal label from RMG-database/input/surface/libraries/metal.py ...
catalystProperties(
    metal='Pt111',
    # coverageDependence=True,   # only uses coverage dependence already present in libraries; RMG does not estimate it
)
# ... OR (not both) explicit binding energies for ALL of C, H, O, N plus a site density:
# catalystProperties(
#     bindingEnergies={
#         'H': (-2.75368, 'eV/molecule'),
#         'C': (-7.02516, 'eV/molecule'),
#         'N': (-4.63225, 'eV/molecule'),
#         'O': (-3.81153, 'eV/molecule'),
#     },
#     surfaceSiteDensity=(2.483e-9, 'mol/cm^2'),
# )

species(
    label='CH4',
    reactive=True,
    structure=SMILES("C"),
)
species(
    label='O2',
    reactive=True,
    structure=adjacencyList(
        """
1 O u1 p2 c0 {2,S}
2 O u1 p2 c0 {1,S}
"""),
)
species(
    label='N2',
    reactive=False,
    structure=SMILES("N#N"),
)
# A vacant site is REQUIRED (it is what initialSurfaceCoverages refers to)
species(
    label='X',
    reactive=True,
    structure=adjacencyList("1 X u0"),
)
# Optional: seed important adsorbates explicitly so their labels stay stable
species(
    label='OX',
    reactive=True,
    structure=adjacencyList(
        """
1 O u0 p2 c0 {2,D}
2 X u0 p0 c0 {1,D}
"""),
)

# forbidden(label='CO2_bidentate', structure=SMILES("O=C(*)O*"))   # '*' is a surface site in SMILES

surfaceReactor(
    temperature=(1000, 'K'),                 # may be a 2-entry range [(T1,'K'),(T2,'K')] with nSims=
    initialPressure=(1.0, 'bar'),            # single value only: ranges raise NotImplementedError in surface.pyx
    initialGasMoleFractions={                # NO ranges allowed here
        'CH4': 0.15,
        'O2': 0.15,
        'N2': 0.7,
    },
    initialSurfaceCoverages={                # NO ranges allowed here
        'X': 1.0,
    },
    surfaceVolumeRatio=(1.e5, 'm^-1'),       # catalyst area / gas volume
    terminationConversion={'CH4': 0.95},
    terminationTime=(0.1, 's'),
    terminationRateRatio=0.01,
    # sensitivity=... is NOT supported for surfaceReactor (raises NotImplementedError)
)

simulator(
    atol=1e-18,
    rtol=1e-12,
)

model(
    toleranceKeepInEdge=0.0,
    toleranceMoveToCore=1e-1,                # EDIT: lower (e.g. 1e-3) for a bigger, more complete model
    toleranceInterruptSimulation=0.1,
    maximumEdgeSpecies=100000,
)

options(
    units='si',
    generateOutputHTML=False,
    generatePlots=False,
    saveEdgeSpecies=False,
    saveSimulationProfiles=False,
)

generatedSpeciesConstraints(
    allowed=['input species', 'reaction libraries'],
    maximumCarbonAtoms=2,
    maximumOxygenAtoms=2,
    maximumSurfaceSites=2,                   # strongly recommended: estimates degrade for >2 sites
)
