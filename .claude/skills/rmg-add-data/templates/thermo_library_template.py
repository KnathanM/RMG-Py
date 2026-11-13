#!/usr/bin/env python
# encoding: utf-8
#
# TEMPLATE RMG thermo library. Entries below are copied from real RMG-database files:
#   index 1  <- input/thermo/libraries/CBS_QB3_1dHR.py        (ThermoData form)
#   index 2  <- input/thermo/libraries/primaryThermoLibrary.py (NASA form)
#   index 3  <- input/thermo/libraries/Chlorination.py         (Wilhoit form)
# Replace them with your own data. Rules:
#   * file name (without .py) is the library label RMG uses; keep `name` identical to it
#   * every `index` must be unique; every label must be unique
#   * `molecule` is a full adjacency list (not SMILES); RMG matches species by structure, not label
#   * units are explicit in every quantity tuple; '+|-' uncertainties are optional

name = "MyThermoLibrary"
shortDesc = u"One-line description (method, who, when)"
longDesc = u"""
Method / level of theory, units, references (DOIs), who computed it.
"""

entry(
    index = 1,
    label = "sBuOH",
    molecule =
"""
1  C u0 p0 c0 {2,S} {3,S} {5,S} {6,S}
2  C u0 p0 c0 {1,S} {4,S} {7,S} {8,S}
3  C u0 p0 c0 {1,S} {9,S} {10,S} {11,S}
4  C u0 p0 c0 {2,S} {12,S} {13,S} {14,S}
5  O u0 p2 c0 {1,S} {15,S}
6  H u0 p0 c0 {1,S}
7  H u0 p0 c0 {2,S}
8  H u0 p0 c0 {2,S}
9  H u0 p0 c0 {3,S}
10 H u0 p0 c0 {3,S}
11 H u0 p0 c0 {3,S}
12 H u0 p0 c0 {4,S}
13 H u0 p0 c0 {4,S}
14 H u0 p0 c0 {4,S}
15 H u0 p0 c0 {5,S}
""",
    thermo = ThermoData(
        Tdata = ([300,400,500,600,800,1000,1500],'K'),
        Cpdata = ([28.21,34.5,40.21,45.08,52.8,58.62,67.9],'cal/(mol*K)','+|-',[1,1,1,1,1,1,1]),
        H298 = (-70.51,'kcal/mol','+|-',2),
        S298 = (83.05,'cal/(mol*K)','+|-',1),
    ),
    shortDesc = u"""CBS-QB3 with 1-D hindered rotors""",
    longDesc =
u"""
Free-text provenance: software, level of theory, rotors, corrections, reference.
""",
)

entry(
    index = 2,
    label = "Ar",
    molecule =
"""
1 Ar u0 p4 c0
""",
    thermo = NASA(
        polynomials = [
            NASAPolynomial(coeffs=[2.5,0,0,0,0,-745.375,4.37967], Tmin=(200,'K'), Tmax=(1000,'K')),
            NASAPolynomial(coeffs=[2.5,0,0,0,0,-745.375,4.37967], Tmin=(1000,'K'), Tmax=(6000,'K')),
        ],
        Tmin = (200,'K'),
        Tmax = (6000,'K'),
    ),
    shortDesc = u"""Burcat Thermo Data""",
    longDesc =
u"""
Ar HF298=0.  REF=C.E. Moore 'Atomic Energy Levels' NSRDS-NBS 35 (1971) p.211
""",
)

entry(
    index = 3,
    label = "CC(Cl)C",
    molecule =
"""
1  C  u0 p0 c0 {2,S} {5,S} {6,S} {7,S}
2  C  u0 p0 c0 {1,S} {3,S} {4,S} {8,S}
3  Cl u0 p3 c0 {2,S}
4  C  u0 p0 c0 {2,S} {9,S} {10,S} {11,S}
5  H  u0 p0 c0 {1,S}
6  H  u0 p0 c0 {1,S}
7  H  u0 p0 c0 {1,S}
8  H  u0 p0 c0 {2,S}
9  H  u0 p0 c0 {4,S}
10 H  u0 p0 c0 {4,S}
11 H  u0 p0 c0 {4,S}
""",
    thermo = Wilhoit(
        Cp0 = (33.2579, 'J/(mol*K)'),
        CpInf = (257.749, 'J/(mol*K)'),
        a0 = -2.74468,
        a1 = 3.80647,
        a2 = -8.18262,
        a3 = 5.18858,
        H0 = (-96.5735, 'kJ/mol'),
        S0 = (-1382.47, 'J/(mol*K)'),
        B = (685.282, 'K'),
    ),
    shortDesc = u"""CBS-QB3 calcs""",
    longDesc =
u"""
""",
)
