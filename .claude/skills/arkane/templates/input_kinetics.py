#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Arkane KINETICS (TST) input template (derived from examples/arkane/reactions/H+C2H4=C2H5).
# A TS file has the same format as a species file (energy, geometry, frequencies with ONE imaginary mode,
# externalSymmetry, spin_multiplicity, opticalIsomers, rotors).

title = 'H + C2H4 <=> C2H5'
modelChemistry = "CBS-QB3"
useHinderedRotors = False
useBondCorrections = True       # BACs apply to species; usually leave corrections as for the species

species('H', 'H.py', structure=SMILES('[H]'))
species('C2H4', 'ethene.py', structure=SMILES('C=C'))
species('C2H5', 'ethyl.py', structure=SMILES('[CH2]C'))
transitionState('TS', 'TS.py')

thermo('H', 'NASA')             # thermo of all species -> consistent reverse rates and Keq
thermo('C2H4', 'NASA')
thermo('C2H5', 'NASA')

reaction(
    label='H + C2H4 <=> C2H5',
    reactants=['H', 'C2H4'],
    products=['C2H5'],
    transitionState='TS',
    tunneling='Eckart',         # 'Eckart' (needs reactant, TS AND product energies) or 'Wigner'; NOT 'Eckhart'
)

statmech('TS')
kinetics(
    label='H + C2H4 <=> C2H5',
    Tmin=(400, 'K'), Tmax=(1200, 'K'), Tcount=6,   # or Tlist=([400, 500, 700, 900, 1100, 1200], 'K')
    # three_params=True,        # default True: fit modified Arrhenius A, n, Ea; False = A, Ea only
)
