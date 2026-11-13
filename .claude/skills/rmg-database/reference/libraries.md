# Commonly used RMG-database libraries (checked against the local RMG-database)

The entry counts come from `grep -c '^entry('`. Names are **case-sensitive** and must match the file or folder name exactly. Before recommending a library, always confirm that it exists locally (`ls`, see SKILL.md §2). Read its `longDesc` header for the source and level of theory.

## Thermo libraries (`input/thermo/libraries/<name>.py`)

| Name | Entries | Use |
|---|---|---|
| `primaryThermoLibrary` | 48 | **Always include.** Small species such as H, H2, O2, H2O, Ar and N2. H and H2 cannot be estimated by group additivity. |
| `BurkeH2O2` | 13 | H2/O2 combustion species from Burke et al. Often listed first in combustion runs (`examples/rmg/commented/input.py`). |
| `thermo_DFT_CCSDTF12_BAC` | 148 | High-level CCSD(T)-F12 values with BAC. Spelled **`F12`** in capitals. |
| `DFT_QCI_thermo` | 217 | General C/H/O species. |
| `CBS_QB3_1dHR` | 44 | CBS-QB3 with 1-D hindered rotors (Goldsmith et al. 2012). |
| `Klippenstein_Glarborg2016` | 68 | Thermo that goes with the `Klippenstein_Glarborg2016` kinetics library. |
| `FFCM1(-)` | 50 | Thermo that goes with the `FFCM1(-)` kinetics library. |
| `GRI-Mech3.0` / `GRI-Mech3.0-N` | 53 / – | Thermo that goes with GRI-Mech 3.0, without and with N. |
| `NOx2018` | 148 | Nitrogen chemistry; goes with the `NOx2018` kinetics library. |
| `CHON_G4`, `CHO_G4`, `CHOF_G4`, `CHOCl_G4`, ... | ~2000 (CHON_G4) | Large G4 small-molecule sets, including halogen variants. |
| `Narayanaswamy`, `SABIC_aromatics_1dHR`, `JetSurF2.0` | 158 / 331 / 342 | Aromatics and jet-fuel species. |
| `SulfurLibrary`, `NISTThermoLibrary`, `halogens` | | Sulfur, NIST, and halogen species. |
| `surfaceThermoPt111`, `surfaceThermoNi111`, `electrocatThermo` | 153 / – / 5 | Surface adsorbates. See `rmg-catalysis`. |

## Kinetics libraries (`input/kinetics/libraries/<name>/reactions.py`; names can be nested paths)

| Name | Entries | Typical role |
|---|---|---|
| `primaryH2O2` | 50 | H2/O2 core chemistry. A common seed for oxidation. |
| `BurkeH2O2inN2`, `BurkeH2O2inArHe` | 30 each | H2/O2 chemistry; pick the version that matches your bath gas. |
| `FFCM1(-)` | 259 | Foundational fuel chemistry (C0–C1). Pair it with the `FFCM1(-)` thermo. |
| `Klippenstein_Glarborg2016` | 582 | High-pressure methane oxidation. Pair it with the thermo of the same name. |
| `GRI-Mech3.0` | 199 | Natural gas without NOx. Pair it with the `GRI-Mech3.0` thermo. |
| `ERC-FoundationFuelv0.9` | 245 | Small-molecule combustion. A common seed. |
| `Glarborg/C0` … `Glarborg/C3`, `Glarborg/highP` | 486 (C3) | Glarborg sub-mechanisms. |
| `combustion_core/version2` … `version5` | 129 (v5) | Core combustion sets. |
| `NOx2018`, `primaryNitrogenLibrary` | 1321 / 442 | Nitrogen chemistry. |
| `primarySulfurLibrary`, `Sulfur/...` | 77 | Sulfur chemistry. |
| `C3` | 37 | Cyclopentadiene pyrolysis with ethene. Used as a reaction library in `examples/rmg/commented`. |
| `Surface/CPOX_Pt/Deutschmann2006_adjusted`, `Surface/Methane/Deutschmann_Ni`, `Surface/Ammonia/...`, `Surface/DOC/...` | | Surface mechanisms. See `rmg-catalysis`. |
| `Aromatics_high_pressure/...`, `JetSurF1.0`, `JetSurF2.0` | | Aromatics and jet fuel. |

## Transport, statmech and solvation

- **Transport libraries:** `PrimaryTransportLibrary`, `GRI-Mech`, `NOx2018`, `OneDMinN2`, `NIST_Fluorine`.
  - `transportLibraries` defaults to `None`, which loads all of them.
  - Missing species fall back to group estimates (`transport/groups/`).
- **Statmech:** `statmech/libraries/halogens_G4.py` (`frequenciesLibraries`). `statmech/groups/groups.py` holds the frequency groups used to estimate densities of states for pdep.
- **Solvation:** `solvation/libraries/{solvent.py, solute.py}` and `solvation/groups/`.

## Kinetics family sets (`input/kinetics/families/recommended.py`)

- The sets are `default`, `ch_pyrolysis`, `liquid_peroxide`, `surface`, `halogens`, `surface_development` and `electrochem`.
- Combine them: `kineticsFamilies=['default', 'surface']`.
- `'all'` loads every family. `'none'` loads none.
- A pure exclusion list such as `['!Intra_Disproportionation']` means "all families except these". You cannot mix `!` and non-`!` names.

Source of truth: the files themselves, plus `documentation/source/users/rmg/input.rst` (Datasources).
