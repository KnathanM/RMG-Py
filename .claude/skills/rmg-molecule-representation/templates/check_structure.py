#!/usr/bin/env python
"""Round-trip check of a structure before using it in RMG.

Usage (run with the RMG Python env; if rmgpy is not importable, set PYTHONPATH=$RMG_PY):
    python check_structure.py "C=C[CH2]"            # SMILES
    python check_structure.py "InChI=1S/CH4/h1H4"   # InChI
    python check_structure.py adjlist.txt           # file containing an adjacency list
Prints the adjacency list, multiplicity, radical count, formula, SMILES, InChI and
resonance structures so a human/agent can confirm the structure is what was meant.
"""
import os
import sys

import os as _os, sys as _sys
try:
    import rmgpy  # noqa: F401
except ImportError:  # rmgpy not pip-installed: use the RMG-Py checkout this skill lives in
    _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *[_os.pardir] * 4)))
from rmgpy.molecule import Molecule
from rmgpy.species import Species


def load(identifier):
    if os.path.isfile(identifier):
        with open(identifier) as f:
            return Molecule().from_adjacency_list(f.read())
    if identifier.startswith('InChI='):
        return Molecule(inchi=identifier)
    return Molecule(smiles=identifier)


def main(identifier):
    mol = load(identifier)
    print('Input        :', identifier)
    print('Formula      :', mol.get_formula())
    print('Multiplicity :', mol.multiplicity)
    print('Radicals     :', mol.get_radical_count())
    print('Net charge   :', mol.get_net_charge())
    print('SMILES out   :', mol.to_smiles())
    try:
        print('InChI        :', mol.to_inchi())
    except Exception as e:  # surface species etc. have no InChI
        print('InChI        : n/a ({0})'.format(e))
    print('Adjacency list:')
    print(mol.to_adjacency_list())
    spc = Species(molecule=[mol])
    spc.generate_resonance_structures()
    print('Resonance structures ({0}):'.format(len(spc.molecule)))
    for i, res in enumerate(spc.molecule):
        print('--- structure {0}: {1}'.format(i, res.to_smiles()))
        print(res.to_adjacency_list())


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
