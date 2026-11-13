#!/usr/bin/env python
# encoding: utf-8
#
# TEMPLATE RMG kinetics library (folder = library; it holds reactions.py + dictionary.txt).
# Entries are copied from real RMG-database libraries (source noted on each); replace with your data.
# Rules enforced when RMG loads the library (rmgpy/data/kinetics/library.py):
#   * every species label in `label` must be defined in dictionary.txt (labels are case-sensitive,
#     must not contain '+', and are split on ' + ' and '<=>' / '=>')
#   * '<=>' = reversible; '=>' requires reversible=False in the entry
#   * reactions must be element-balanced, max 3 reactants and 3 products
#   * a specific collider like (+N2) must appear on BOTH sides and N2 must be in the dictionary;
#     Troe/Lindemann/ThirdBody entries are written WITHOUT (+M) in the label (see entries 3-5)
#   * duplicate reactions need duplicate=True (or combine them in MultiArrhenius)
#   * units: give units explicitly; bimolecular A in cm^3/(mol*s) or m^3/(mol*s), unimolecular s^-1,
#     termolecular / low-pressure limits cm^6/(mol^2*s)
#   * indices unique; keep `name` equal to the folder name (RMG uses the folder name as the label)

name = "MyKineticsLibrary"
shortDesc = u"One-line description"
longDesc = u"""
Source, level of theory, bath gas, T and P ranges, references (DOIs).
"""

# Plain modified Arrhenius  k = A (T/T0)^n exp(-Ea/RT)          [primaryH2O2, index 15]
entry(
    index = 1,
    label = "H + O2 <=> OH + O",
    degeneracy = 1,
    kinetics = Arrhenius(A=(1.04e+14, 'cm^3/(mol*s)'), n=0, Ea=(15286, 'cal/mol'), T0=(1, 'K'),
                         Tmin=(1100, 'K'), Tmax=(3370, 'K')),
    shortDesc = u"""[Konnov2015]""",
    longDesc = u"""Table 1, Reaction 8""",
)

# Sum of Arrhenius expressions (a duplicate reaction)          [Glarborg/C1, index 4]
entry(
    index = 2,
    label = "O + H2 <=> OH + H",
    degeneracy = 1,
    duplicate = True,
    kinetics = MultiArrhenius(
        arrhenius = [
            Arrhenius(A=(3.8e+12, 'cm^3/(mol*s)'), n=0, Ea=(7948, 'cal/mol'), T0=(1, 'K')),
            Arrhenius(A=(8.8e+14, 'cm^3/(mol*s)'), n=0, Ea=(19175, 'cal/mol'), T0=(1, 'K')),
        ],
    ),
)

# Third-body reaction; efficiency keys are SMILES (need not be in dictionary.txt)   [primaryH2O2, index 1]
entry(
    index = 3,
    label = "H + H <=> H2",
    kinetics = ThirdBody(
        arrheniusLow = Arrhenius(A=(7e+17, 'cm^6/(mol^2*s)', '*|/', 2), n=-1.0, Ea=(0, 'cal/mol'), T0=(1, 'K'),
                                 Tmin=(77, 'K'), Tmax=(5000, 'K')),
        efficiencies = {'[Ar]': 0.0, '[He]': 0.0, 'N#N': 0.0, '[H]': 0.0, '[H][H]': 0.0, '[O][O]': 0.0, 'O': 14.3}),
    shortDesc = u"""[Konnov2015]""",
)

# Lindemann fall-off                                           [Dooley/methylformate, index 680]
entry(
    index = 4,
    label = "CO + O <=> CO2",
    degeneracy = 1,
    kinetics = Lindemann(
        arrheniusHigh = Arrhenius(A=(1.8e+10, 'cm^3/(mol*s)'), n=0, Ea=(2384, 'cal/mol'), T0=(1, 'K')),
        arrheniusLow = Arrhenius(A=(1.55e+24, 'cm^6/(mol^2*s)'), n=-2.79, Ea=(4191, 'cal/mol'), T0=(1, 'K')),
        efficiencies = {'[H][H]': 2.5, '[C-]#[O+]': 1.9, 'O=C=O': 3.8, 'O': 12, '[Ar]': 0.87},
    ),
)

# Troe fall-off; elementary_high_p=True marks arrheniusHigh as a true elementary high-P limit
# so RMG may also use this reaction inside its own pressure-dependent networks.   [Dooley/methylformate, index 678]
entry(
    index = 5,
    label = "H + O2 <=> HO2",
    degeneracy = 1,
    elementary_high_p = True,
    kinetics = Troe(
        arrheniusHigh = Arrhenius(A=(1.475e+12, 'cm^3/(mol*s)'), n=0.6, Ea=(0, 'cal/mol'), T0=(1, 'K')),
        arrheniusLow = Arrhenius(A=(6.366e+20, 'cm^6/(mol^2*s)'), n=-1.72, Ea=(524.8, 'cal/mol'), T0=(1, 'K')),
        alpha = 0.8,
        T3 = (1e-30, 'K'),
        T1 = (1e+30, 'K'),
        efficiencies = {'[H][H]': 2, '[C-]#[O+]': 1.9, '[O][O]': 0.78, 'O=C=O': 3.8, 'O': 11},
    ),
)

# PLOG: Arrhenius at a list of pressures                       [primaryNitrogenLibrary, index 6]
entry(
    index = 6,
    label = "CH2(S) + N2 <=> CH2N2",
    degeneracy = 1,
    kinetics = PDepArrhenius(
        pressures = ([1, 10, 100, 300, 760, 7600], 'torr'),
        arrhenius = [
            Arrhenius(A=(1.22e+30, 'cm^3/(mol*s)'), n=-7.25, Ea=(2730, 'cal/mol'), T0=(1, 'K'), Tmin=(300, 'K'), Tmax=(3000, 'K')),
            Arrhenius(A=(9.45e+30, 'cm^3/(mol*s)'), n=-7.22, Ea=(2734, 'cal/mol'), T0=(1, 'K'), Tmin=(300, 'K'), Tmax=(3000, 'K')),
            Arrhenius(A=(4.55e+31, 'cm^3/(mol*s)'), n=-7.13, Ea=(2653, 'cal/mol'), T0=(1, 'K'), Tmin=(300, 'K'), Tmax=(3000, 'K')),
            Arrhenius(A=(1.46e+32, 'cm^3/(mol*s)'), n=-7.13, Ea=(2774, 'cal/mol'), T0=(1, 'K'), Tmin=(300, 'K'), Tmax=(3000, 'K')),
            Arrhenius(A=(7.41e+32, 'cm^3/(mol*s)'), n=-7.21, Ea=(3088, 'cal/mol'), T0=(1, 'K'), Tmin=(300, 'K'), Tmax=(3000, 'K')),
            Arrhenius(A=(1.39e+34, 'cm^3/(mol*s)'), n=-7.28, Ea=(3804, 'cal/mol'), T0=(1, 'K'), Tmin=(300, 'K'), Tmax=(3000, 'K')),
        ],
    ),
    shortDesc = u"""[Lin2010a]""",
)

# Chebyshev k(T,P); kunits must match the reaction molecularity   [2006_Joshi_OH_CO, index 2]
entry(
    index = 7,
    label = "OH + CO <=> H + CO2",
    degeneracy = 1,
    kinetics = Chebyshev(
        coeffs = [
            [10.89, -0.4346, -0.2152, -0.05574],
            [0.6535, 0.4928, 0.2262, 0.03006],
            [0.2008, -0.01527, 0.01434, 0.02917],
            [0.07196, -0.03864, -0.01717, 0.00435],
            [0.02016, -0.02204, -0.01345, 0.002451],
            [0.01154, 0.01113, 0.0004633, -0.01646],
        ],
        kunits = 'cm^3/(mol*s)',
        Tmin = (300, 'K'),
        Tmax = (2500, 'K'),
        Pmin = (0.001, 'atm'),
        Pmax = (641.5, 'atm'),
    ),
)
