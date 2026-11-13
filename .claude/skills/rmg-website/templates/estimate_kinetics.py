#!/usr/bin/env python
"""Local equivalent of rmg.mit.edu "Kinetics Search" for one family: generate reactions of the reactants and
estimate k with the same family.get_kinetics() call RMG uses (rmgpy/rmg/model.py generate_kinetics).
Run from a scratch dir with the RMG Python env (PYTHONPATH=$RMG_PY if rmgpy is not importable).
Usage: python estimate_kinetics.py FAMILY SMILES1 [SMILES2]     e.g.  H_Abstraction CCC "[OH]"
Notes: libraries are not searched (set reaction_libraries and use db.kinetics.generate_reactions_from_libraries
for that); thermo_libraries should match your RMG run because BM families and reverse rates use dH_rxn."""
import sys
import os as _os, sys as _sys
try:
    import rmgpy  # noqa: F401
except ImportError:  # rmgpy not pip-installed: use the RMG-Py checkout this skill lives in
    _sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), *[_os.pardir] * 4)))
from rmgpy import settings
from rmgpy.data.rmg import RMGDatabase
from rmgpy.species import Species
family_label, smiles = sys.argv[1], sys.argv[2:]
db = RMGDatabase()
db.load(settings['database.directory'],
        thermo_libraries=['primaryThermoLibrary'],   # same thermo libraries as your RMG run, in the same order
        reaction_libraries=[],
        kinetics_families=[family_label],            # load only what you need; 'default' is slow
        kinetics_depositories=['training'],
        depository=False, solvation=False)           # keep surface=True: surface=False skips loading thermo in 3.3.0
fam = db.kinetics.families[family_label]
if not fam.auto_generated:                           # hand-built trees: what RMG does at start-up
    fam.add_rules_from_training(thermo_database=db.thermo)
    fam.fill_rules_by_averaging_up(verbose=True)
reactants = [Species(smiles=s) for s in smiles]
for s in reactants:
    s.generate_resonance_structures()
rxns = db.kinetics.generate_reactions_from_families(reactants, products=None, only_families=[family_label])
for rxn in rxns:
    for sp in rxn.reactants + rxn.products:
        if sp.thermo is None:
            sp.thermo = db.thermo.get_thermo_data(sp)
    kin, source, entry, is_forward = fam.get_kinetics(rxn, template_labels=rxn.template, degeneracy=rxn.degeneracy,
                                                      estimator='rate rules', return_all_kinetics=False)
    rxn.kinetics = kin
    if not is_forward:
        print('(kinetics matched in the reverse direction)')
        rxn.reactants, rxn.products = rxn.products, rxn.reactants
    rxn.fix_barrier_height()                         # converts Blowers-Masel (ArrheniusBM) to Arrhenius using dH_rxn
    print('\n', rxn, ' | source:', source)
    print('  ', rxn.kinetics)
    print('   k(1000 K) = %.3e (SI units: m^3/(mol*s) for bimolecular)' % rxn.kinetics.get_rate_coefficient(1000))
