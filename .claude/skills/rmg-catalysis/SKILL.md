---
name: rmg-catalysis
description: Builds heterogeneous-catalysis (gas-surface) mechanisms with RMG, the former RMG-Cat. Covers catalystProperties (a metal label such as Pt111/Ni111/Cu111, or custom C/H/O/N binding energies plus site density for hypothetical metals or screening; coverageDependence), the surfaceReactor and liquidSurfaceReactor blocks, the surface database setup (the 'surface' family set, surfaceThermoPt111, adsorptionGroups, Surface/ kinetics libraries), maximumSurfaceSites, writing adsorbates in adjacency lists and SMILES (X sites, physisorbed/vdW, bidentate), surface outputs (chem-gas.inp/chem-surface.inp, the Cantera SURF0 phase), example inputs, and current limitations. Use when the user says "catalysis", "surface mechanism", "RMG-Cat", "adsorbate", "Pt(111)", "binding energies", "linear scaling", "surfaceReactor", "sticking coefficient", "coverage dependence", "methane partial oxidation on platinum", "CO2 reduction", "X in adjacency list", or "physisorbed".
---

# RMG for catalytic (gas-surface) systems

Based on the 2025 RMG Workshop talk “RMG for Catalytic Systems” and RMG-Py 3.3.0.

RMG-Cat has been merged into RMG, so there is nothing extra to install. RMG models gas-surface chemistry of C, H and O on **single-crystal pure-metal terrace sites**, with N partly supported. Gas-phase families run alongside the surface families, so catalytic ignition followed by gas-phase combustion is captured. Run modes and paths are covered in **rmg-install**; launching jobs is covered in **rmg-run-job**.

## 1. Start from the verified template

`templates/input_surface.py` is adapted from `examples/rmg/minimal_surface` and `catalysis/ch4_o2`. It was checked with `read_input_file` against this checkout. Copy it to a new run folder, edit the `EDIT` lines, and run it as usual. The unmodified `minimal_surface` example takes about 3 minutes and gives 29 core species and 98 reactions.

Example inputs in this repo (`examples/rmg/`):

| Example | Shows |
|---|---|
| `minimal_surface/` | Explicit `bindingEnergies` + `surfaceSiteDensity`, `maximumSurfaceSites=2`, seeded adsorbates |
| `catalysis/ch4_o2/` | `metal='Pt111'`, CPOX library, and an RMS notebook `simulate_ch4o2cat_RMS.ipynb` |
| `catalysis/methane_steam/` | Ni(111) binding energies and site density |
| `liquid_cat/` | `liquidSurfaceReactor` + `solvation` (RMS) |
| `CO2RR/` | Electrocatalysis on `Ag111`: `electrochem` families, `surfPotential`/`liqPotential`, proton `1 H u0 p0 c+1`, `electrocatThermo` |
| `minimal_multisurf/` | **Not catalysis.** This is the core/edge "surface" *algorithm* (`toleranceMoveEdgeReactionToSurface`) |

## 2. `catalystProperties(...)`

Signature: `catalystProperties(bindingEnergies=None, surfaceSiteDensity=None, metal=None, coverageDependence=False)` in `rmgpy/rmg/input.py`.

- **Either** `metal='Pt111'` **or** `bindingEnergies` + `surfaceSiteDensity`. Giving both raises `InputError` (tested).
- Metal labels in `RMG-database/input/surface/libraries/metal.py`: Pt111, Ru0001, Rh111, Ir111, Au111, Pd111, Cu111, Ag111, Ni111, Co0001, Pt211, Rh211, Ag211, Pd211, Au211, Ir211, Ru211, Co211, Ni211, Cu211, Li110, Fe110.
- `bindingEnergies` must contain **all four** of C, H, O and N, e.g. `{'C': (-7.02516,'eV/molecule'), ...}`. Use this for hypothetical metals in descriptor screening studies.
- If you give neither, both default to Pt(111).
- `coverageDependence=True` uses coverage-dependent parameters **already present in libraries**, and writes them to Chemkin/Cantera. RMG does **not estimate** coverage dependence. Libraries that contain some include `Surface/CPOX_Pt/Deutschmann2006_adjusted`, `Surface/Methane/Deutschmann_Pt`, `Surface/Methane/Vlachos_Pt111`, `Surface/Methane/Vlachos_Rh`, `Surface/DOC/*` and `Surface/Ammonia/Vlachos_Ru0001`. Grep for `coverage` in the library to confirm.

How adsorbate thermo is estimated (from the talk): RMG looks for the species in a library first. If it isn't there, it takes the gas-phase precursor thermo, adds an adsorption correction from a Pt(111) DFT-based tree (about 160 adsorbates), then shifts to the target metal with **linear scaling relations** (Abild-Pedersen et al. 2007). Expect errors of about 0.3 eV, comparable to DFT error. The X in the structure stands for the *preferred* site (atop, bridge or hollow are not distinguished).

## 3. Database block for surfaces

```python
database(
    thermoLibraries=['surfaceThermoPt111', 'primaryThermoLibrary', 'thermo_DFT_CCSDTF12_BAC', 'DFT_QCI_thermo'],
    reactionLibraries=[('Surface/CPOX_Pt/Deutschmann2006_adjusted', False)],
    kineticsFamilies=['surface', 'default'],     # sets from kinetics/families/recommended.py
    kineticsDepositories=['training'], seedMechanisms=[], kineticsEstimator='rate rules',
    # adsorptionGroups='adsorptionPt111',        # default; others: adsorptionNi111, adsorptionLi
)
```

- Family sets in `RMG-database/input/kinetics/families/recommended.py`:
  - `surface` (21 families): adsorption (single, dissociative, vdW, bidentate), dissociation, abstraction, and their vdW/beta/double variants.
  - `surface_development`: Eley-Rideal (`Surface_EleyRideal_Addition_Multiple_Bond`) and `Surface_Migration`. These are **not** in `surface`. Add them explicitly if you want them, because the talk presents them as available.
  - `electrochem`. You can also list individual families, or `'!Name'` to exclude one.
- Surface thermo libraries: `surfaceThermoPt111`, `surfaceThermoNi111`, `surfaceThermoLi`, `electrocatThermo`, `electrocatLiThermo`.
- Surface kinetics libraries (under `RMG-database/input/kinetics/libraries/Surface/`): `CPOX_Pt/Deutschmann2006_adjusted`, `Methane/{Deutschmann_Ni, Deutschmann_Ni_full, Deutschmann_Pt, Vlachos_Pt111, Vlachos_Rh}`, `Ammonia/*` (Pt, Pd, Rh, Ru, Ni), `DOC/*`, `Hydrazine/{Roldan_Cu111, Roldan_Ir111}`, `Example`. Pick one that matches your metal. The docs (`surfaces.rst`) still use old names (`Deutschmann2006`, `adsorptionPt.py`); use the names on disk.
- Surface rate forms: `SurfaceArrhenius` (per-site units) and `StickingCoefficient` (0 to 1 × collision rate). Many surface families rely on BEP estimates because the trees are sparse.

## 4. Reactors

**`surfaceReactor`** is native RMG: constant volume, isothermal, solved in moles, including vacant sites.

```python
surfaceReactor(temperature=(1000,'K'), initialPressure=(1.0,'bar'),
    initialGasMoleFractions={'CH4':0.15, 'O2':0.15, 'N2':0.7},
    initialSurfaceCoverages={'X':1.0},
    surfaceVolumeRatio=(1.e5,'m^-1'),
    terminationConversion={'CH4':0.95}, terminationTime=(0.1,'s'), terminationRateRatio=0.01)
```

Verified behaviour:
- **Temperature range**: OK, e.g. `temperature=[(800,'K'),(1000,'K')], nSims=3`.
- **Pressure range**: fails with `NotImplementedError: Can't do ranges of initial pressures for surface reactors yet` (`rmgpy/solver/surface.pyx`). `input.py` accepts it, but the solver rejects it.
- **Mole fraction or coverage ranges**: rejected.
- **`sensitivity=`**: `NotImplementedError: Can't currently do sensitivity with surface reactors.` Do sensitivity afterwards in Cantera or RMS.
- Gas mole fractions are renormalized if they don't sum to 1.
- You need a vacant-site species (`adjacencyList("1 X u0")`) and must list it in `initialSurfaceCoverages`.
- Use several `surfaceReactor` blocks to cover uncertain conditions.

**`liquidSurfaceReactor`** is RMS-backed and needs Julia/RMS (see **rmg-rms**). It also needs `solvation(solvent=...)`. Arguments: `temperature, initialConcentrations, initialSurfaceCoverages, surfaceVolumeRatio, distance, viscosity, surfPotential, liqPotential, termination*, constantSpecies`. No ranges. In this version the `viscosity` argument is mis-stored (it uses `distance`). This contradicts the talk's statement that RMS surface reactors are not reachable from RMG: this one is. There is no RMS *gas*-surface reactor keyword.

**Species constraints:** keep the number of sites small. Estimates get worse for species with more surface sites.

```python
generatedSpeciesConstraints(allowed=['input species','reaction libraries'],
    maximumSurfaceSites=2,            # strongly recommended
    # maximumSurfaceBondOrder=...,   # also valid
    maximumCarbonAtoms=2, maximumOxygenAtoms=2)
```

## 5. Writing adsorbates

`X` is the surface site. All of these were tested with `Species().from_adjacency_list`:

```
vacant site:            1 X u0
O=X (chemisorbed O):    1 O u0 p2 c0 {2,D}
                        2 X u0 p0 c0 {1,D}
CH#X (monodentate):     1 C u0 p0 c0 {2,S} {3,T}
                        2 H u0 p0 c0 {1,S}
                        3 X u0 p0 c0 {1,T}
H2 physisorbed (no bond to X):
                        1 H u0 p0 c0 {2,S}
                        2 H u0 p0 c0 {1,S}
                        3 X u0 p0 c0
H2O physisorbed (explicit vdW bond, also accepted):
                        1 O u0 p2 c0 {2,S} {3,S} {4,vdW}
                        2 H u0 p0 c0 {1,S}
                        3 H u0 p0 c0 {1,S}
                        4 X u0 p0 c0 {1,vdW}
bidentate X-CH2-O-X:    1 C u0 p0 c0 {2,S} {3,S} {4,S} {5,S}
                        2 O u0 p2 c0 {1,S} {6,S}
                        3 H u0 p0 c0 {1,S}
                        4 H u0 p0 c0 {1,S}
                        5 X u0 p0 c0 {1,S}
                        6 X u0 p0 c0 {2,S}
```

- In SMILES, `*` is a site: `O=*`, `C*`, `[H][H].*` (physisorbed), `O=C(*)O*` (bidentate CO2). Output SMILES and pictures draw X as **Pt** whatever the metal (`[O]=[Pt]`, `[H][H].[Pt]`). Labels in output files can look like `C.[Pt](22)`.
- Atom types for writing *groups* and family templates: `X` (any site), `Xv` (vacant), `Xo` (occupied). A physisorbed species' X has no bonds, so its atom type is `Xv`.
- Bond orders: `vdW` = 0 (used temporarily in recipes, then removed), `H` (hydrogen bond) = 0.1, `R` = 0.05.
- To keep RMG from making a structure, use `forbidden(label='CO2_bidentate', structure=SMILES("O=C(*)O*"))`.
- More on adjacency lists is in **rmg-molecule-representation**.

## 6. Outputs and simulating them

- Chemkin: `chemkin/chem-gas.inp` + `chem-surface.inp` (and the `chem_annotated-*` versions). The surface file starts with `SITE/SURF0/ SDEN/...`. For older-style tools, load them with `load_chemkin_file(gas, dict, surface_path=surface)` (see **rmg-scripting-tools**).
- Cantera: a single `cantera/chem.yaml` / `chem_annotated.yaml` with phases `gas` and **`SURF0`** (`thermo: ideal-surface`, `site-density` in mol/cm²). Load with `ct.Interface(yaml, "SURF0", [gas])`. A tested surface reactor snippet is in **rmg-simulate-cantera** section 5.
- RMS: `rms/chemN.rms` with phases `gas` and `surface`. For a multiphase setup see **rmg-rms** section 7.
- `diffModels.py` handles surface models: it looks for `-surface.inp` next to each Chemkin file.

## 7. Limitations (talk + code)

- Pure metals only: no oxides, zeolites or supports. There is a **single site type** (no step and terrace together; multi-site support is in development).
- Any material can be modeled if you supply parameters (libraries or trees) and the site can be represented as X. At that point it is a parameter-estimation problem.
- Pressure dependence combined with catalysis is untested, according to the presenter.
- Arkane is gas-phase only. Use Pynta for automated surface DFT; see **pynta**.
- Coverage-dependent *thermo*, resonance of adsorbates such as bidentate formate, and better site specificity were described as in progress at the time of the talk.
- If a non-oxidative system misbehaves (for example, unexpected O species), the presenter asked for a GitHub issue with details (see **rmg-contributing**).
- Workflow advice from the talk: treat RMG as a collaborator. Build, simulate, do sensitivity or degree-of-rate-control analysis, compute the important parameters (DFT/Pynta), add them back (**rmg-add-data**), and rerun. Catalysis models depend heavily on uncertain parameters, so Bayesian uncertainty quantification is a promising approach.

## Key papers

- First RMG-Cat paper: doi:10.1021/acs.jpcc.7b02133
- Pt(111) adsorbate data: doi:10.1021/acs.iecr.9b01464
- Linear scaling in RMG: doi:10.1021/acscatal.0c04100
- RMG database paper: doi:10.1021/acs.jcim.2c00965

These DOIs were shared by the speaker in the workshop chat. They were not checked against the papers.

## Agent notes

- Surface runs can grow quickly. Start with `maximumSurfaceSites=2`, C/O limits and a loose `toleranceMoveToCore`, run in the background, and ask before launching multi-hour jobs.
- Don't edit `metal.py` or the surface libraries in the shared database to add a metal. Use `bindingEnergies` in the input file, or follow **rmg-add-data** with the user's consent.

**When unsure:** check `rmgpy/rmg/input.py` (`catalyst_properties`, `surface_reactor`, `liquid_cat_reactor`, `generated_species_constraints`), `rmgpy/solver/surface.pyx`, `RMG-database/input/kinetics/families/recommended.py`, `RMG-database/input/surface/libraries/metal.py`, `documentation/source/users/rmg/surfaces.rst` (watch for stale names), and `examples/rmg/minimal_surface/input.py`.
