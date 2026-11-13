#!/usr/bin/env python
"""Convert a Chemkin mechanism + RMG species dictionary into an RMG thermo library and kinetics library,
written to an OUTPUT directory of your choice (unlike RMG-database/scripts/importChemkinLibrary.py, which
always writes into the installed RMG-database). Same conversion calls as importChemkinLibrary.py.

Usage (RMG Python env; if rmgpy is not importable, set PYTHONPATH=$RMG_PY):
    python chemkin_to_library.py CHEMKIN_FILE SPECIES_DICTIONARY NAME OUTPUT_DIR [--thermo THERM_FILE]
Writes:  OUTPUT_DIR/NAME.py                      (thermo library; only species that have thermo)
         OUTPUT_DIR/NAME/reactions.py + dictionary.txt   (kinetics library)
The species dictionary must give an adjacency list for every Chemkin species name (RMG format).
"""
import argparse
import logging
import os

import os as _os, sys as _sys
try:
    import rmgpy  # noqa: F401
except ImportError:  # rmgpy not pip-installed: use the RMG-Py checkout this skill lives in
    _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *[_os.pardir] * 4)))
from rmgpy.chemkin import load_chemkin_file
from rmgpy.data.base import Entry
from rmgpy.data.kinetics import KineticsLibrary
from rmgpy.data.thermo import ThermoLibrary

parser = argparse.ArgumentParser()
parser.add_argument('chemkin')
parser.add_argument('dictionary')
parser.add_argument('name')
parser.add_argument('output_dir')
parser.add_argument('--thermo', default=None, help='separate Chemkin THERMO file, if not inside CHEMKIN')
args = parser.parse_args()

species_list, reaction_list = load_chemkin_file(args.chemkin, args.dictionary, thermo_path=args.thermo)

thermo_library = ThermoLibrary(name=args.name)
for i, spc in enumerate(species_list):
    if spc.thermo:
        thermo_library.load_entry(index=i + 1, label=spc.label,
                                  molecule=spc.molecule[0].to_adjacency_list(), thermo=spc.thermo)
    else:
        logging.warning('Species {0} has no thermo; omitted from thermo library.'.format(spc.label))

kinetics_library = KineticsLibrary(name=args.name)
kinetics_library.entries = {}
for i, rxn in enumerate(reaction_list):
    entry = Entry(index=i + 1, label=rxn.to_labeled_str(), item=rxn, data=rxn.kinetics)
    entry.long_desc = rxn.kinetics.comment
    kinetics_library.entries[i + 1] = entry
kinetics_library.check_for_duplicates(mark_duplicates=True)
kinetics_library.convert_duplicates_to_multi()

os.makedirs(os.path.join(args.output_dir, args.name), exist_ok=True)
thermo_library.save(os.path.join(args.output_dir, args.name + '.py'))
kinetics_library.save(os.path.join(args.output_dir, args.name, 'reactions.py'))
kinetics_library.save_dictionary(os.path.join(args.output_dir, args.name, 'dictionary.txt'))
print('Wrote {0} thermo entries and {1} reactions to {2}'.format(
    len(thermo_library.entries), len(kinetics_library.entries), os.path.abspath(args.output_dir)))
