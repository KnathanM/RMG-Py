#!/usr/bin/env python
# encoding: utf-8
# Arkane THERMO input template (derived from examples/arkane/species/C2H4 and C2H6).
# Run:  python $RMG_PY/Arkane.py input.py          (writes output.py etc. next to this file)

title = 'My species thermo'

# 1. Level of theory: a known string (see documentation/source/users/arkane/input.rst table) ...
modelChemistry = "CBS-QB3"
# ... or explicit (software must match the log files):
# modelChemistry = LevelOfTheory(method='wb97m-v', basis='def2-tzvpd', software='qchem')
# Different energy and frequency levels:
# modelChemistry = CompositeLevelOfTheory(
#     freq=LevelOfTheory(method='B3LYP', basis='6-31G(d,p)', software='gaussian'),
#     energy=LevelOfTheory(method='CCSD(T)-F12', basis='cc-pVTZ-F12', software='molpro'))

# 2. Corrections / settings (defaults shown)
# frequencyScaleFactor = 0.99   # default: looked up from the level of theory, else 1.0 (check arkane.log)
useHinderedRotors = True        # default True; uses `rotors` in the species file
useAtomCorrections = True       # default True (AEC + SOC). Needs tabulated values or atomEnergies below
useBondCorrections = False      # default False
bondCorrectionType = 'p'        # 'p' = Petersson (uses `bonds`), 'm' = Melius
# useIsodesmicReactions = False # True forces AEC on and BAC off
# atomEnergies = {'H': -0.499818, 'C': -37.785385, 'O': -75.064580}   # Hartree, ONLY for unlisted levels of theory

# 3. Species: label, species file (or .yml), and a structure (needed for BAC from structure, RMG libraries, YAML)
species('C2H4', 'ethene.py',
        structure=SMILES('C=C'))

# 4. Jobs
thermo('C2H4', 'NASA')          # or 'Wilhoit'
# statmech('C2H4')              # partition-function info only
