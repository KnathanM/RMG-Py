---
name: arkane
description: Runs and writes inputs for Arkane, RMG's statistical-mechanics tool. Arkane turns quantum-chemistry output (Gaussian, Molpro, Orca, Q-Chem, Psi4, TeraChem logs) into thermochemistry (NASA/Wilhoit), TST rate coefficients with Eckart/Wigner tunneling, and pressure-dependent networks (master equation) with automatic network exploration. Covers model chemistry and corrections (AEC/BAC/isodesmic), species and TS files, rotors, outputs including RMG_libraries, and pitfalls. Use when the user says "run Arkane", "compute thermo from my Gaussian log", "get a rate from my TS calculation", "TST rate with tunneling", "hindered rotor scan", "pressure-dependent network in Arkane", "explorer job", "bond additivity corrections", "convert QM results into an RMG library", or "why are my Arkane energies wrong".
---

# Arkane: QM results → thermo, kinetics, pressure-dependent networks

Based on the 2025 RMG Workshop talk “Introduction to Arkane” and RMG-Py 3.3.0.

- Arkane ships inside RMG-Py (`$RMG_PY/arkane/`, `$RMG_PY/Arkane.py`). It needs no separate install. See `rmg-install` for detecting a conda or Docker setup (`/rmg/RMG-Py`).
- Arkane does **not** run the QM calculations. The user must already have the log files. ARC is the separate tool that automates QM and calls Arkane.
- Arkane is **gas phase only**: no surfaces or catalysis (use Pynta, see `pynta`) and no liquids.

## 1. Run it

```bash
conda activate rmg_env     # the env's bin/ must be on PATH: Arkane calls the `symmetry` program
python $RMG_PY/Arkane.py input.py              # output goes next to input.py
python $RMG_PY/Arkane.py input.py -o OUTDIR    # other flags: -q quiet | -v verbose | -d debug | -p/--no-plot
```
- If `symmetry` is not on PATH, the run fails with `Running symmetry on the point group calculation has failed`. This happens even when `externalSymmetry` is given. Fix it by activating the env or adding its `bin/` to PATH.
- In Docker, run the same command inside the container.
- Paths inside the input are relative to the input file.

**Test the setup first** (about 10 s). Copy an example into scratch, never run it inside the repo:
```bash
mkdir -p /tmp/arkane_test && cp -r $RMG_PY/examples/arkane/species/C2H4 /tmp/arkane_test/
cd /tmp/arkane_test/C2H4 && python $RMG_PY/Arkane.py input.py && grep "Enthalpy of formation" output.py
#   Enthalpy of formation (298 K)   =    13.432 kcal/mol
```
- Many examples point at shared files with relative paths. For example, `reactions/H+C2H4=C2H5` uses `../../species/H/H.py`. Copy the whole `examples/arkane/{species,reactions}` tree, or fix the paths.
- Ask before running large pdep or explorer jobs. They load the RMG database and use many CPU cores. The acetyl+O2 CSE network took about 40 s wall time and about 5 CPU-min.

## 2. Input file structure (`arkane/input.py`)

An input file has four parts: (1) the level of theory, (2) corrections, (3) species and TS definitions, (4) jobs. The templates were all tested by running them:
- [templates/input_thermo.py](templates/input_thermo.py): thermo for a species.
- [templates/species_file.py](templates/species_file.py): the per-species or TS file.
- [templates/input_kinetics.py](templates/input_kinetics.py): TST rate.
- [templates/input_network.py](templates/input_network.py): pdep network, abridged.

| Top-level variable | Default | Notes |
|---|---|---|
| `modelChemistry` | none | One of: a string such as `"CBS-QB3"` or `'CCSD(T)-F12/cc-pVTZ-F12//B3LYP/6-311++G(3df,3pd)'`; `LevelOfTheory(method=, basis=, software=)`; or `CompositeLevelOfTheory(freq=LevelOfTheory(...), energy=LevelOfTheory(...))`. The `energy` dict keys in species files must match its energy level. |
| `frequencyScaleFactor` | looked up from the level of theory, else 1.0 | Check `arkane.log`. A value inside a species file is ignored, with a warning. |
| `useHinderedRotors` | `True` | Uses the `rotors` from species files. |
| `useAtomCorrections` | `True` | AEC + SOC. Values come from `$RMG_DB/input/quantum_corrections/data.py`. If the level of theory is not tabulated, give `atomEnergies = {'H': ..., 'C': ...}` in Hartree. Otherwise the energies are meaningless. |
| `useBondCorrections` | **`False`** | Turn it on for thermo where BACs exist for the level of theory. |
| `bondCorrectionType` | `'p'` | `'p'` is Petersson, which uses `bonds` or the structure. `'m'` is Melius. |
| `useIsodesmicReactions` | `False` | `True` forces AEC on and BAC off. Optional `referenceSets`. Needs a `structure`. See `examples/arkane/species/Pentyl_isodesmic`. |
| `author`, `title`, `description` | | Metadata. |

- Levels of theory with tabulated AEC, BAC, SOC and frequency scale factors are listed in `documentation/source/users/arkane/input.rst`. Examples: CBS-QB3 (0.990), wb97x-d3/def2-tzvp (0.984), wb97m-v/def2-tzvpd (1.002), M06-2X/cc-pVTZ (0.955), B3LYP/6-31G(d,p) (0.961).
- Ask the user for the level of theory. Never guess it from file names.

Definitions and jobs:
- `species(label, 'file.py' or 'file.yml', structure=SMILES('...'))`
  - The `structure` (also `adjacencyList`, `InChI`) is needed for BACs from the structure, isodesmic reactions, YAML output and RMG libraries. Round-trip it (`rmg-molecule-representation`).
  - The inline form takes keywords instead of a file: `E0=`, `modes=[...]`, `spinMultiplicity=`, `opticalIsomers=`, `molecularWeight=`, `collisionModel=TransportData(...)`, `energyTransferModel=SingleExponentialDown(...)`, `thermo=`, `reactive=False`. A file and keywords can be combined.
- `transitionState(label, 'TS.py')`. The TS file has the same format as a species file, with exactly one imaginary frequency. The inline form adds `frequency=(-1679,'cm^-1')`.
- `reaction(label, reactants=[...], products=[...], transitionState='TS', tunneling='Eckart')`
  - `tunneling` is `'Eckart'` or `'Wigner'`, case-insensitive. `'Eckhart'`, which appears in the docs table, raises `Unknown tunneling model`.
  - Alternatively, give `kinetics=Arrhenius(...)` with no TS, e.g. for a barrierless channel in a network.
  - With neither a TS nor kinetics, Arkane estimates the rate from the RMG database. That needs a `database()` block.
- Jobs:
  - `thermo(label, 'NASA' | 'Wilhoit')`
  - `statmech(label)`
  - `kinetics(label, Tmin=, Tmax=, Tcount= | Tlist=, three_params=True, sensitivity_conditions=None)`
  - `pressureDependence(...)`, `explorer(...)`
  - `ae(...)` / `bac(...)` fit new corrections. See `examples/arkane/bac/`.

## 3. Species / TS file (`arkane/statmech.py` `StatMechJob.load`)

```python
bonds = {'C-C': 1, 'C-H': 6}        # Petersson BAC only; derived from structure if omitted
linear = False                      # optional
externalSymmetry = 6                # optional (computed with `symmetry` if omitted) -- CHECK it
spin_multiplicity = 1               # 3.3.0 reads THIS key (see gotcha)
opticalIsomers = 1                  # optional
energy = {'CBS-QB3': Log('ethane_cbsqb3.log'), 'Klip_2': -79.64199436}
geometry = Log('ethane_cbsqb3.log') # optional, defaults to the frequencies log
frequencies = Log('ethane_cbsqb3.log')  # REQUIRED
rotors = [HinderedRotor(scanLog=Log('ethane_scan_1.log'), pivots=[1, 5], top=[1, 2, 3, 4], fit='best')]
```

Ways to give the energy (the meaning matters):

| Form | Interpreted as | Corrections |
|---|---|---|
| `Log('x.log')` | electronic energy read from the log | Arkane adds ZPE, AEC and BAC |
| `-79.64199436` (float) | electronic energy in **Hartree, without ZPE** | ZPE, AEC and BAC added |
| `(-79.64, 'hartree', 'e_electronic')` | same, with explicit units | added |
| `(-205.3, 'kJ/mol')` or `(..., 'E0')` | **E0 including ZPE, used as is** | **none added**. You must put it on the same reference as every other species. |

Rotors:
- `HinderedRotor(scanLog=, pivots=, top=, symmetry=None, fit='best'|'cosine'|'fourier')`
  - `pivots` is the bonded atom pair. `top` is the atoms on one side, *including* its pivot. Indices are 1-based.
  - The scan should start at the minimum. Use `ScanLog('scan.csv')` for tabulated data.
- `FreeRotor(pivots, top, symmetry)`
- `HinderedRotor1DArray(angles, energies, pivots, top, symmetry, fit)`
- `HinderedRotor2D(...)` and `HinderedRotorClassicalND(...)` (see `examples/arkane/species/Toluene_*`)
- With Gaussian, rotors need `geometry` and `frequencies` from the **same** log. The frequency job also needs `iop(7/33=1)`, otherwise "Force Constant Matrix Missing" appears and the rotors are ignored.

The log parser is picked automatically by `Log()`. `GaussianLog`, `MolproLog`, `OrcaLog`, `QChemLog`, `Psi4Log` and `TeraChemLog` also work.

## 4. Pressure dependence and explorer (keywords differ from RMG!)

```python
network(label='acetyl + O2', isomers=['acetylperoxy', 'hydroperoxylvinoxy'],
        reactants=[('acetyl', 'oxygen')], bathGas={'nitrogen': 1.0})
pressureDependence('acetyl + O2', Tmin=(300,'K'), Tmax=(2000,'K'), Tcount=8,
        Pmin=(0.01,'bar'), Pmax=(100,'bar'), Pcount=5, maximumGrainSize=(1.0,'kcal/mol'),
        minimumGrainCount=250, method='modified strong collision', interpolationModel=('chebyshev', 6, 4),
        activeJRotor=True, activeKRotor=True)
explorer(source=['CH3', 'CH2O'], explore_tol=0.1, energy_tol=np.inf, flux_tol=0.0,
         bathGas={'N2': 1.0}, maximumRadicalElectrons=1)
```

| RMG input (`rmgpy/rmg/input.py`) | Arkane input (`arkane/input.py`) |
|---|---|
| `temperatures=(300, 2000, 'K', 8)` | `Tmin=(300,'K'), Tmax=(2000,'K'), Tcount=8` or `Tlist=` |
| `pressures=(0.01, 100, 'bar', 5)` | `Pmin=, Pmax=, Pcount=` or `Plist=` |
| `minimumNumberOfGrains=250` | `minimumGrainCount=250` |
| `interpolation=('Chebyshev', 6, 4)` | `interpolationModel=('chebyshev', 6, 4)` or `('pdeparrhenius',)` |
| `maximumAtoms`, `completedNetworks` | none |

More points:
- `method` is one of `'modified strong collision'` (robust), `'reservoir state'`, `'chemically-significant eigenvalues'` (more accurate, can fail at low T), or the simulation-least-squares variants. See `examples/arkane/networks/*` and `rmg-pressure-dependence`.
- Isomers need `collisionModel=TransportData(sigma=, epsilon=)`. If `energyTransferModel` is omitted, RMG's default is generated.
- Bath gases need `reactive=False` and `molecularWeight` (or a structure).
- `explorer` must come **after** `pressureDependence`, and it needs a `database(...)` block. Examples: `examples/arkane/explorer/{methoxy, methyl+formaldehyde}`.
- Limit an explorer run with `maximumRadicalElectrons`, `energy_tol` and `explore_tol`.
- RMG writes Arkane-format network files to `output/pdep/` (see `rmg-pressure-dependence`).

## 5. Outputs (in the input folder or `-o`)

- `output.py`: conformers, thermo tables, NASA/Wilhoit fits, k(T) with and without tunneling, Keq, the reverse rate, Arrhenius fits, and `pdepreaction(...)` blocks.
- `chem.inp`, `species_dictionary.txt`, `arkane.log`, `supporting_information.csv`, `plots/`.
- `species/*.yml`: Arkane YAML. It can be reloaded with `species('X', 'X.yml')`.
- `paths/` for reactions, `network.pdf` for pdep, and `sensitivity/`.
- `RMG_libraries/`: ready-made RMG libraries.
  - With thermo jobs only, it contains `thermo.py`.
  - If the job has any kinetics or pdep reactions, it contains `reactions.py` + `dictionary.txt` **and `thermo.py` is deleted**. `save_kinetics_lib` removes the folder first (`arkane/output.py`). This was verified with the `H+C2H4=C2H5` example.
  - Run the thermo jobs separately if you need both.
  - To use these files in RMG, see `rmg-add-data` (external library by path).

## 6. Gotchas (verified in 3.3.0)

- **`spinMultiplicity` in species *files* is silently ignored.** The docs and the examples use `spinMultiplicity = N`, but `statmech.py` reads `spin_multiplicity`. Tested: `spinMultiplicity = 4` in `C2H5/ethyl.py` still gave `spin_multiplicity = 2` from the log, while `spin_multiplicity = 4` changed S298.
  - Usually the log's multiplicity is right. Write `spin_multiplicity` when you must override it.
  - Inline `species(..., spinMultiplicity=2)` keywords *are* read.
- **E0 vs H0.** A tuple energy is taken as E0 with ZPE and gets no corrections. A float is a bare electronic energy that gets corrected. At the workshop, a user group passed something they thought was E0. It was effectively an enthalpy of formation at 0 K on a different reference, and debugging took a long time. Ask the user exactly what each number is, and keep all species in a network on one reference.
- **Symmetry numbers and multiplicities.** Check them by hand. Do not copy them from the examples, which do not always set everything. Wrong `externalSymmetry` shifts S by R·ln σ.
- If `useAtomCorrections` is on but the level of theory is not tabulated and there is no `atomEnergies`, the energies are not meaningful. Read `arkane.log` warnings such as `Atom corrections are not being used. Do not trust energies and thermo.`
- BACs are for thermo. Rate calculations rely on error cancellation, so BACs are generally not used for TSs (talk).
- Abnormally large energies in `network.pdf` usually mean inconsistent species definitions, such as wrong atoms or references.
- Every Arkane `reaction` is marked `elementary_high_p=True`, so its kinetics can be used by RMG pdep when imported as a library.

When unsure, the source of truth is `arkane/input.py` (input keywords and defaults), `arkane/statmech.py` (species-file keys, energy handling, rotors), `arkane/main.py` (CLI flags, outputs), `arkane/output.py`, `documentation/source/users/arkane/*.rst`, and `examples/arkane/`.
