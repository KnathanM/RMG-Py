#!/usr/bin/env python
# encoding: utf-8
# Arkane PRESSURE-DEPENDENCE input template (derived from examples/arkane/networks/acetyl+O2_cse).
# Keyword names differ from RMG's pressureDependence() block -- see SKILL.md.
# Species can be given inline (E0 + modes, as below) or from a species file plus keywords, e.g.
#   species('acetylperoxy', 'acetylperoxy.py', structure=SMILES('CC(=O)O[O]'),
#           collisionModel=TransportData(...), energyTransferModel=SingleExponentialDown(...))
# Isomers need collisionModel; if energyTransferModel is omitted, RMG's default model is generated.
# Every species/TS listed below the network must be defined; this template is abridged -- see the full
# example in examples/arkane/networks/acetyl+O2_cse/input.py (it runs in ~40 s).

title = 'acetyl + oxygen'

species(
    label='acetylperoxy',
    structure=SMILES('CC(=O)O[O]'),
    E0=(-34.6, 'kcal/mol'),     # E0 incl. ZPE; all E0 in a network must share one reference
    modes=[
        IdealGasTranslation(mass=(75.04, "g/mol")),
        NonlinearRotor(inertia=([54.2977, 104.836, 156.05], "amu*angstrom^2"), symmetry=1),
        HarmonicOscillator(frequencies=([319.695, 500.474, 536.674, 543.894, 727.156, 973.365, 1037.77, 1119.72,
                                         1181.55, 1391.11, 1449.53, 1454.72, 1870.51, 3037.12, 3096.93, 3136.39],
                                        "cm^-1")),
    ],
    spinMultiplicity=2,         # keyword form: spinMultiplicity IS read here (arkane/input.py species())
    opticalIsomers=1,
    molecularWeight=(75.04, "g/mol"),
    collisionModel=TransportData(sigma=(5.09, 'angstrom'), epsilon=(473, 'K')),       # needed for isomers
    energyTransferModel=SingleExponentialDown(alpha0=(0.5718, 'kcal/mol'), T0=(300, 'K'), n=0.85),
)
# ... more species: reactant pairs need E0 + modes; products likewise ...

species(
    label='nitrogen',
    structure=SMILES('N#N'),
    molecularWeight=(28.04, "g/mol"),
    collisionModel=TransportData(sigma=(3.70, 'angstrom'), epsilon=(94.9, 'K')),
    reactive=False,             # bath gas
)

transitionState(
    label='isom1',
    E0=(-5.8, 'kcal/mol'),
    modes=[],                   # fill like species modes
    spinMultiplicity=2,
    opticalIsomers=1,
    frequency=(-1679.04, 'cm^-1'),   # imaginary frequency
)

reaction(label='isom1', reactants=['acetylperoxy'], products=['hydroperoxylvinoxy'],
         transitionState='isom1', tunneling='Eckart')
# barrierless entrance channel: give high-P kinetics instead of TS statmech
# reaction(label='entrance1', reactants=['acetyl', 'oxygen'], products=['acetylperoxy'],
#          transitionState='entrance1', kinetics=Arrhenius(A=(2.65e6, 'm^3/(mol*s)'), n=0, Ea=(0, 'kcal/mol'), T0=(1, 'K')))

network(
    label='acetyl + O2',
    isomers=['acetylperoxy', 'hydroperoxylvinoxy'],
    reactants=[('acetyl', 'oxygen')],          # bimolecular source channels
    bathGas={'nitrogen': 1.0},
)

pressureDependence(
    'acetyl + O2',                              # network label
    Tmin=(300.0, 'K'), Tmax=(2000.0, 'K'), Tcount=8,     # or Tlist=
    Pmin=(0.01, 'bar'), Pmax=(100.0, 'bar'), Pcount=5,   # or Plist=
    maximumGrainSize=(1.0, 'kcal/mol'),
    minimumGrainCount=250,
    method='modified strong collision',         # | 'reservoir state' | 'chemically-significant eigenvalues' | ...
    interpolationModel=('chebyshev', 6, 4),     # or ('pdeparrhenius',)
    activeJRotor=True,
    # activeKRotor=True, sensitivity_conditions=[[(1000, 'K'), (1, 'bar')]],
)
