#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Arkane SPECIES / TS file template (derived from examples/arkane/species/C2H6/C2H6.py and C2H4/ethene.py).
# Paths are relative to this file. Supported log parsers: Log() auto-detects Gaussian, Molpro, Orca, QChem,
# Psi4, TeraChem; GaussianLog/MolproLog/... names also work.

bonds = {'C-C': 1, 'C-H': 6}    # only for Petersson BACs; derived from `structure` if omitted

linear = False                  # optional; auto-detected from geometry if omitted
externalSymmetry = 6            # CHECK by hand (ethane = 6); if omitted, Arkane computes it with `symmetry`
spin_multiplicity = 1           # NOTE: 3.3.0 reads `spin_multiplicity`; the documented `spinMultiplicity`
                                # key is silently ignored and the multiplicity in the log file is used
opticalIsomers = 1              # if omitted, determined from the geometry

# Energy: dict keyed by level of theory (the key matching modelChemistry's energy level is used), or a single value.
#   Log('x.log')                -> electronic energy read from log; ZPE, AEC/BAC are added by Arkane
#   -79.64199436                -> float = electronic energy in Hartree WITHOUT ZPE; corrections added
#   (-205.3, 'kJ/mol')          -> E0 INCLUDING ZPE, used as is: NO AEC/BAC/ZPE added (be sure of its reference!)
#   (-79.64, 'hartree', 'e_electronic') or (..., 'E0') -> explicit meaning
energy = {
    'CBS-QB3': Log('ethane_cbsqb3.log'),
    'Klip_2': -79.64199436,
}

geometry = Log('ethane_cbsqb3.log')     # optional; defaults to the frequencies log
frequencies = Log('ethane_cbsqb3.log')  # REQUIRED (Hessian). With rotors + Gaussian: same log as geometry,
                                        # and the freq job needs iop(7/33=1) so the force constants are printed

# 1-D hindered rotors from relaxed scans (scan should start at the minimum; use ScanLog('scan.csv') for raw data)
#   pivots = the two atoms of the rotating bond; top = atoms on one side INCLUDING its pivot atom (1-based indices)
#   symmetry = rotor symmetry number (auto-determined if omitted); fit = 'best' | 'cosine' | 'fourier'
rotors = [HinderedRotor(scanLog=Log('ethane_scan_1.log'), pivots=[1, 5], top=[1, 2, 3, 4], fit='best')]
# rotors = [FreeRotor(pivots=[1, 5], top=[1, 2, 3, 4], symmetry=3)]
# Also available: HinderedRotor1DArray(angles, energies, pivots, top, symmetry, fit),
#                 HinderedRotor2D(...), HinderedRotorClassicalND(...)   (see examples/arkane/species/Toluene_*)
