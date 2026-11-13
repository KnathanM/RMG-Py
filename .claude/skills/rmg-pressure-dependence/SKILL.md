---
name: rmg-pressure-dependence
description: Configures and debugs pressure-dependent kinetics in RMG-Py mechanism generation. Covers the pressureDependence() block (method, grains, T/P grids, Chebyshev or PDepArrhenius/PLOG interpolation, maximumAtoms, completedNetworks), the inert bath-gas requirement, keeping reactor T/P inside the pdep ranges, controlling runtime, reading the pdep/ network files with Arkane and generatePESDiagrams, the library flags elementary_high_p and allow_pdep_route, and common pdep errors. Use it when the user says "turn on pressure dependence", "do I need pdep", "falloff / Chebyshev / PLOG rates in RMG", "InvalidMicrocanonicalRateError", "No unreactive species to identify as bath gas", "Reaction system T is above pressure_dependence range", "RMG is slow with pdep", "debug a pdep network", or "RMG added well-skipping reactions on top of my library".
---

# Pressure dependence in RMG

Based on the 2025 RMG Workshop talk “Pressure Effects in RMG” (Bill Green's material, presented by Richard West) and RMG-Py 3.3.0.

This skill covers **RMG's automatic pdep during mechanism generation**. For a careful master-equation study of one network with quantum-chemistry inputs, use the `arkane` skill. Arkane uses different keyword names (see the end of this file). Writing and running the job itself: `rmg-run-job`.

## When pressure dependence matters (answer: almost always in gas phase)
- Unimolecular reactions and association/dissociation reactions are pressure dependent when collisions can't thermalize the energized adduct faster than it reacts. The rate coefficient then depends on P and on the bath gas. Chemically activated well-skipping (A+B → C* → D* → E+F) creates net reactions that match no reaction family.
- It is strongest for **small molecules, high T, and low P** (a few Torr in lab experiments). It also matters at the high pressures of engines.
- Lab experiments and real devices often sit on opposite sides of the falloff region. Check whether a measured rate is a pdep rate or a high-P rate.
- **RMG does no pdep estimation unless a `pressureDependence()` block is present.** Pressure-dependent rates that come from libraries or seeds (Troe, Chebyshev, PLOG) are still used as given.
- The `minimal` and `superminimal` examples have **no** pdep block. Users who copy them forget to turn it on, and turning it on can change the model a lot (the presenter's halogen work is one example). `examples/rmg/ethane-oxidation` and `examples/rmg/commented` include it.
- RMG's pdep estimates are rough: maybe within an order of magnitude. That is still better than leaving pdep out.
- Usually skip pdep for liquid phase and surfaces.

## 1. Add the block
```python
pressureDependence(
    method='modified strong collision',   # recommended for RMG runs: robust and fast
    maximumGrainSize=(0.5,'kcal/mol'),
    minimumNumberOfGrains=250,
    temperatures=(300, 2200, 'K', 10),    # (Tmin, Tmax, units, Tcount)
    pressures=(0.01, 100, 'bar', 10),     # (Pmin, Pmax, units, Pcount)
    interpolation=('Chebyshev', 6, 4),    # or ('PDepArrhenius',) for PLOG output
    maximumAtoms=15,                      # no pdep for adducts with more than 15 atoms (H included)
    # completedNetworks=['CH2O2'],        # formulas of trusted networks that RMG must not expand
)
```

| keyword | default in code | notes |
|---|---|---|
| `method` | required | Use `'modified strong collision'` (MSC; recommended; robust when the inputs are crude). Also accepted: `'reservoir state'` (no longer recommended as the default), `'chemically-significant eigenvalues'` (CSE; most accurate with good inputs, but fails at low T and with poor estimates, so use it in Arkane, not RMG), and the `'simulation least squares'` variants (`rmgpy/pdep/network.py`). **A typo is only caught when the first network is solved** (`NetworkError: Unknown method`) |
| `temperatures`, `pressures` | required | 4-tuples. For Chebyshev the points lie on a Gauss–Chebyshev grid; for PDepArrhenius they are evenly spaced in 1/T. They cover the whole interpolation range |
| `interpolation` | `None`, which **crashes** | Must be `('Chebyshev', nT, nP)` or `('PDepArrhenius',)` (case-insensitive). The Chebyshev basis counts must be **less than** Tcount and Pcount (`KineticsError` otherwise, raised mid-run); there is a warning if the count is below 1.25× the basis size |
| `maximumGrainSize`, `minimumNumberOfGrains` | 0.0, 0 | Always set both. 0.5 kcal/mol and 250 are the standard values. More grains are more accurate but slower |
| `maximumAtoms` | None (no limit) | Biggest runtime lever. Larger molecules have more modes, so they sit closer to the high-P limit |
| `completedNetworks` | None | A list of formulas, e.g. `['CH2O2', 'C2H6']`. RMG adds no new reactions to these networks; seed and library reactions are still used |

Related options:
- `options(generatePESDiagrams=True)` draws a PDF of each network into `pdep/`.
- `model(ignoreOverallFluxCriterion=True)` applies `toleranceMoveToCore` only to network exploration.

## 2. Required companions (checked when the job starts)
1. **An inert bath gas in the reactor.** At least one `reactive=False` species must appear in the reactor's `initialMoleFractions`. Otherwise you get `AssertionError: Pressure Dependence calculations require at least one inert (nonreacting) species for the bath gas` (`main.py check_input`).
   - Use e.g. `species(label='N2', reactive=False, structure=SMILES("N#N"))`, or Ar/He to match the experiment.
2. **Reactor T and P strictly inside the pdep ranges**, including the ends of ranged reactors. Otherwise: `AssertionError: Reaction system T is above pressure_dependence range` (or below, or `P`). Give some margin, e.g. Tmin=300 K and Tmax 200–500 K above the hottest reactor.
3. **Bath-gas composition is not your mole fractions.** RMG weights *every* `reactive=False` core species **equally** (`rmg/pdep.py`).
   - RMG always auto-adds Ar, He, Ne and N2 as inert species. Ar and He that arrive through a seed or library are reactive by default, but auto-added ones are not.
   - So a propane/air run with an H2/O2 seed ends up with bathGas `{N2: 0.5, Ne: 0.5}`. This was verified in a 3.3.0 test run (see the `pdep/network*.py` files).
   - Collision efficiencies therefore don't exactly match the experiment's diluent. Mention this to the user when the bath gas matters.
4. **Collision and energy-transfer data:**
   - Lennard-Jones σ/ε come from the transport libraries in order (`transportLibraries`, which loads all libraries if omitted), then group/Joback estimates.
   - ⟨ΔE_down⟩ is hard-coded for every species: `SingleExponentialDown(alpha0=3.5886 kJ/mol, T0=300 K, n=0.85)` (`rmgpy/species.py`).
   - Densities of states come from the statmech frequency groups plus an inverse Laplace transform of k∞. If you add new elements (e.g. halogens), the statmech groups in `RMG-database/input/statmech/groups/` need matching functional groups too.

## 3. Runtime: what it costs and how to limit it
Every network expansion triggers a new master-equation solve at every (T, P) grid point. Pdep is a major cost early in a run, alongside reaction generation. To limit it:
- Set `maximumAtoms`: 10–16 for combustion of larger fuels.
- Don't use huge T/P grids. 8–10 points each with `('Chebyshev', 6, 4)` is typical (examples use 8×5).
- Keep `minimumNumberOfGrains` at about 250 for generation. Converge grains in Arkane later for the networks that matter.
- Mark trusted networks as `completedNetworks`.
- Loosen `toleranceMoveToCore` in early iterations. Network exploration also uses this tolerance.
- `-n` parallelism speeds up only reaction generation, not the master-equation solves.
- Ask the user before launching long pdep runs. Run them in the background with `-t` (see `rmg-run-job`).
- **Pruning combined with pdep:** the presenter recalled problems with this combination in the past and was not sure of the current state. Pruning code does delete empty networks (`model.py prune`). If you combine them, check the results.

## 4. Library reactions inside pdep networks (trusted networks, well-skipping)
Kinetics library flags (in each library's `reactions.py` entry; documented in `documentation/source/users/rmg/database/modification.rst`):
- **`elementary_high_p=True`**: the entry is an *elementary* unimolecular, association or dissociation reaction whose kinetics represent or contain the **high-P limit**. That means Troe/Lindemann, PLOG/Chebyshev up to ≥ 90 bar (the code's threshold), or an Arrhenius that is truly k∞. RMG then uses k∞ as a path reaction in its networks.
  - Without this flag (the default), library reactions are *not* put into networks.
  - With the flag, an Arrhenius library rate may be replaced by RMG's network-derived PLOG/Chebyshev.
  - Examples: `Klippenstein_Glarborg2016`, `FFCM1(-)`, `GRI-Mech3.0`.
- **`allow_pdep_route=True`**: if RMG derives a network reaction with the same reactants and products as this library reaction, keep **both**. Use this when separate well-skipping channels exist alongside the library pathway.
  - Without the flag (the default), the network reaction is dropped. The log says `Network reaction ... matched an existing core/edge reaction ... from the X library, and was not added to the model`.

Pitfall: RMG may add its own estimated channels to a network that the library authors had deliberately pruned as too slow, and those estimates can make the model worse. The talk left this open. In 3.3.0, list the network's formula in **`completedNetworks`** to stop RMG from expanding it. Editing library flags changes the shared RMG-database, so tell the user first (`rmg-add-data`).

For well-studied small-molecule chemistry (e.g. OH + CO), prefer a trusted pdep library as a seed or reaction library over RMG's estimates. Do careful Arkane calculations for the networks that sensitivity analysis flags, then add them back as a library (`arkane`, `rmg-add-data`).

## 5. Output and debugging
- **Chemkin output:** Chebyshev gives `CHEB`/`TCHEB`/`PCHEB` lines; PDepArrhenius gives `PLOG` lines. Cantera YAML gets `type: Chebyshev` or `type: pressure-dependent-Arrhenius`.
  - In `chem_annotated.inp`, pdep net reactions carry the comment `! PDep reaction: PDepNetwork #N` instead of a family name. A rate with no family source is often a pdep net reaction.
- **`pdep/networkN_M.py`** (N = network index, M = number of isomers) is an Arkane-format input. A new file is saved each time the network is updated. `pdep/final/networkK_reduced.py` appears after network reduction.
- **Reproduce and visualize a network** in a scratch directory. This writes `network.pdf` (PES diagram), `output.py`, `chem.inp` and `plots/`:
  ```bash
  mkdir /tmp/pdep_debug && cp $JOB/pdep/network4_1.py /tmp/pdep_debug/ && cd /tmp/pdep_debug
  python $RMG_PY/Arkane.py network4_1.py
  ```
  When a master-equation solve fails with `InvalidMicrocanonicalRateError`, RMG itself draws `networkN_M.pdf` into the **top-level output directory**.
- **TS energy offset warning from the talk:** the presenter said the saved files had all TS energies shifted by a constant. In local RMG-Py 3.3.0 this is **fixed**: commit `d5152bc3f` (July 2025) writes `E0 = (<value> - <energy_correction>, "kJ/mol"), # removing the applied energy_correction` for each `transitionState`.
  - If you see that comment, the TS energies are consistent with the species E0s.
  - Files from older RMG versions (e.g. 3.2.0 Docker) still have the offset; use them only qualitatively.
  - The species E0s and frequencies are still RMG *estimates*.
- **Common messages** (more in `rmg-run-job/reference/log-messages.md`):

| message | cause | fix |
|---|---|---|
| `Reaction system T/P is above/below pressure_dependence range` | Reactor is outside the pdep grid | Widen `temperatures`/`pressures` |
| `...require at least one inert (nonreacting) species for the bath gas` / `No unreactive species to identify as bath gas` | No inert species | Add a `reactive=False` species with a mole fraction |
| `TypeError: 'NoneType' object is not subscriptable` when reading the input (pdep block present) | `interpolation` missing | Add `interpolation=('Chebyshev',6,4)` |
| `KineticsError: The master equation data needs more temperature and pressure data points` | Chebyshev basis count ≥ Tcount or Pcount | Raise the counts or lower the basis |
| `NetworkError: Unknown method` | Typo in `method` | Fix the spelling |
| `InvalidMicrocanonicalRateError` (+ PDF drawn) | Usually a badly estimated input: an energy too high, a rate too fast, or a k(T) that isn't really k∞ (odd T^n), so the inverse Laplace transform fails | Inspect the PDF and the network file in Arkane. Fix the offending thermo or rate (library entry), or exclude it via `maximumAtoms`/`completedNetworks` |
| `k(T,P) for net reaction ... exceeds high-P k(T) by F` | Grain discretization or bad inputs | Large F on an important reaction: test more grains in Arkane |
| `PressureDependenceError: Path reaction ... with no high-pressure-limit kinetics` | A library pdep reaction entered a network without a usable k∞ | Check its `elementary_high_p` flag and kinetics type |
| Log shows repeated retries with more grains and finally gives up | Hard network | Debug that network in Arkane as above |

## RMG vs Arkane keyword names (don't mix them)
| RMG `pressureDependence()` | Arkane `pressureDependence()` |
|---|---|
| `temperatures=(Tmin,Tmax,'K',N)` | `Tmin=(..,'K')`, `Tmax=`, `Tcount=` (or `Tlist=`) |
| `pressures=(Pmin,Pmax,'bar',N)` | `Pmin=`, `Pmax=`, `Pcount=` (or `Plist=`) |
| `minimumNumberOfGrains` | `minimumGrainCount` |
| `interpolation` | `interpolationModel` |
| bath gas = all inert core species | `network(..., bathGas={'N2':1.0})` |
| — | `label=`, `activeKRotor`, `activeJRotor`, `sensitivity_conditions` |
See `arkane` and `arkane/input.py`.

## When unsure
Sources of truth:
- `rmgpy/rmg/input.py`: `pressure_dependence()`.
- `rmgpy/rmg/main.py` `check_input()`: range and bath-gas assertions.
- `rmgpy/rmg/pdep.py`: network update, bath gas, file output.
- `rmgpy/rmg/model.py`: `maximumAtoms`, completed networks, library flags.
- `rmgpy/pdep/network.py`: methods.
- `arkane/pdep.py`: grids, fitting, saved files.
- `documentation/source/users/rmg/input.rst` ("Pressure Dependence") and the RMG theory guide on pressure dependence.
