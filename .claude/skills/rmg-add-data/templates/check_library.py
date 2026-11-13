#!/usr/bin/env python
"""Check that a new RMG thermo library file and/or kinetics library folder loads, using the same
loader code RMG uses for external libraries. Does not modify anything.

Usage (RMG Python env; if rmgpy is not importable, set PYTHONPATH=$RMG_PY):
    python check_library.py path/to/MyThermo.py
    python check_library.py path/to/MyKineticsLibrary/          # folder holding reactions.py + dictionary.txt
    python check_library.py MyThermo.py MyKineticsLibrary/      # several at once
"""
import os
import sys

import os as _os, sys as _sys
try:
    import rmgpy  # noqa: F401
except ImportError:  # rmgpy not pip-installed: use the RMG-Py checkout this skill lives in
    _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *[_os.pardir] * 4)))
from rmgpy.data.kinetics import KineticsDatabase
from rmgpy.data.thermo import ThermoDatabase


def check_thermo(path):
    db = ThermoDatabase()
    db.load_libraries(os.path.dirname(path), libraries=[path])   # full .py path -> treated as external
    lib = db.libraries[db.library_order[0]]
    print('Thermo library {0!r}: {1} entries'.format(lib.label, len(lib.entries)))
    for entry in sorted(lib.entries.values(), key=lambda e: e.index):
        mol = entry.item
        h298 = entry.data.get_enthalpy(298) / 1000.
        s298 = entry.data.get_entropy(298)
        print('  {0:>4} {1:<20} {2:<10} mult={3} H298={4:9.2f} kJ/mol S298={5:7.2f} J/mol/K  SMILES={6}'.format(
            entry.index, entry.label, mol.get_formula(), mol.multiplicity, h298, s298, mol.to_smiles()))


def check_kinetics(path):
    path = os.path.abspath(path.rstrip(os.sep))
    db = KineticsDatabase()
    db.load_libraries(os.path.dirname(path), libraries=[path])     # existing folder path -> treated as external
    lib = list(db.libraries.values())[0]
    print('Kinetics library {0!r}: {1} entries'.format(lib.label, len(lib.entries)))
    for entry in sorted(lib.entries.values(), key=lambda e: e.index):
        try:  # evaluate the kinetics object directly (Reaction.get_rate_coefficient can crash outside a model)
            k = '{0:.3e}'.format(entry.data.get_rate_coefficient(1000., 1e5))
        except Exception as e:  # e.g. T outside a Chebyshev range
            k = 'n/a ({0})'.format(e)
        print('  {0:>4} {1:<40} {2:<16} k(1000 K, 1 bar) = {3} (SI)'.format(
            entry.index, entry.label, type(entry.data).__name__, k))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for p in sys.argv[1:]:
        if os.path.isdir(p):
            check_kinetics(p)
        elif p.endswith('.py') and os.path.isfile(p):
            check_thermo(p)
        else:
            sys.exit('Not a thermo .py file or kinetics library folder: {0}'.format(p))
    print('OK: all libraries loaded.')
