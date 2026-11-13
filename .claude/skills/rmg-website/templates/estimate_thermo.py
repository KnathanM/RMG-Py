#!/usr/bin/env python
"""Local equivalent of rmg.mit.edu "Molecule Search -> Search thermochemistry".

Usage (RMG Python env; if rmgpy is not importable, set PYTHONPATH=$RMG_PY; run from a scratch dir):
    python estimate_thermo.py "CCO" "C[CH2]"            # thermo as RMG would pick it (libraries below, then GAV/HBI)
    python estimate_thermo.py --all "CCO"               # every library hit + the group-additivity estimate (slower)
Edit LIBRARIES to match the thermoLibraries of your RMG input (order = priority, first match wins).
"""
import sys

import os as _os, sys as _sys
try:
    import rmgpy  # noqa: F401
except ImportError:  # rmgpy not pip-installed: use the RMG-Py checkout this skill lives in
    _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *[_os.pardir] * 4)))
from rmgpy import settings
from rmgpy.data.thermo import ThermoDatabase
from rmgpy.species import Species

LIBRARIES = ['primaryThermoLibrary', 'DFT_QCI_thermo']

args = sys.argv[1:]
show_all = '--all' in args
smiles_list = [a for a in args if a != '--all'] or ['CCO']

db = ThermoDatabase()
db.load(settings['database.directory'] + '/thermo', libraries=None if show_all else LIBRARIES)

for smi in smiles_list:
    spc = Species(smiles=smi)
    spc.generate_resonance_structures()
    print('\n{0}  formula={1}  multiplicity={2}'.format(smi, spc.molecule[0].get_formula(), spc.molecule[0].multiplicity))
    if show_all:
        for data, library, entry in db.get_all_thermo_data(spc):
            src = library.label if library is not None else 'estimate (GAV/HBI)'
            print('  {0:<30} H298={1:9.2f} kJ/mol  S298={2:7.2f} J/mol/K'.format(
                src, data.get_enthalpy(298) / 1000, data.get_entropy(298)))
    else:
        thermo = db.get_thermo_data(spc)
        print('  H298 = {0:.2f} kJ/mol   S298 = {1:.2f} J/mol/K'.format(thermo.get_enthalpy(298) / 1000,
                                                                    thermo.get_entropy(298)))
        print('  Cp(300 K) = {0:.2f}  Cp(1000 K) = {1:.2f} J/mol/K'.format(thermo.get_heat_capacity(300),
                                                                         thermo.get_heat_capacity(1000)))
        print('  G(1000 K) = {0:.2f} kJ/mol'.format(thermo.get_free_energy(1000) / 1000))
        print('  source:', thermo.comment)
