---
name: pynta
description: Explains what Pynta does and where it fits with RMG. Pynta is a separate workflow package that automates periodic DFT on metal surfaces (adsorbate thermochemistry, surface and gas-surface reaction kinetics, and coverage dependence) and produces RMG libraries and RMS files. The skill covers its required inputs, the prerequisite convergence studies, and the workflow (Fireworks/MongoDB, HFSP transition-state guesses, Sella, IRC, active-learning coverage dependence). Use when the user says "Pynta", "DFT for adsorbates", "surface transition states", "compute catalysis parameters", "coverage dependence from DFT", "ARC for surfaces", "HFSP", or "how do I get better surface rate constants for RMG". Pynta is not in RMG-Py or RMG-database, so check its own docs for install and API details.
---

# Pynta: automated surface DFT for RMG catalysis models

Based on the 2025 RMG Workshop talk “Pynta” and RMG-Py 3.3.0.

**Pynta is a separate package.** Nothing in RMG-Py or RMG-database references it, and it is not installed with RMG. Everything below comes from the talk alone. For installation, input-file syntax, CLI and API, **ask the user where their Pynta checkout is, or look up Pynta's own README/docs online. Do not guess function names, config keys or commands.**

## What it is

Pynta is the surface counterpart of ARC, which automates gas-phase quantum chemistry. It automates periodic-DFT workflows for:
- adsorbate thermochemistry
- surface and gas-surface reaction kinetics, including transition-state searches
- coverage dependence (the effect of co-adsorbates)

Automation matters because surfaces have very many configurations. Even a small 3×3 low-index slab has about 4 unique sites, about 80 ways to place two adsorbates for a TS, and about 500 co-adsorbate placements. The choice of TS configuration changed barriers by 0.2–0.4 eV in the presenter's examples, which is a 40–400× change in rate at 700 K.

## What the user must provide (per the talk)

- **Reactions as RMG adjacency lists** for reactants and products, with **atom labels that map the reacting atoms**, so Pynta can tell which bonds break and form. Example: H2 over two X sites → 2 HX. See **rmg-molecule-representation** and **rmg-catalysis** for X/adsorbate syntax.
- **Slab and surface info**: the slab (ASE/XYZ), surface type or facet, metal, repeats, and a "surrogate" metal used by ACAT for site finding.
- **Quantum-chemistry settings**: an ASE calculator, the software, and its settings. Any ASE-compatible calculator works, including machine-learned potentials (OCP and DeePMD-kit have been used). xTB is the default for cheap pre-optimizations.
- **Fireworks/MongoDB configuration**, for job management on the cluster. Fireworks has a GUI for tracking jobs.

Do these **before** running Pynta, for your DFT method:
- optimize the lattice constant (Pynta can do this for simple surfaces)
- converge the plane-wave cutoff
- converge the k-points
- identify sites (ACAT; automatic for simple surfaces)

The presenter said a preprocessing notebook to automate these steps was "coming soon".

## Workflow (conceptual)

1. **Isolated calculations.** Adsorbate placement and optimization, frequencies, and TS search.
2. **TS guesses with HFSP** (harmonically forced saddle point). An SIDT model predicts how far each breaking or forming bond stretches. Those predicted lengths become spring constraints, and the structure is optimized at low level (xTB, about 30 s per guess). Because each guess is so cheap, *every* reactant/product placement is tried. Guesses with high spring strain are filtered out. The rest are optimized with **Sella** and validated by **IRC**. The low level of theory matters little here, because the springs constrain the key degrees of freedom.
3. **Post-processing notebook.** It fits thermo and kinetics, checks IRCs and frequencies, and validates structures. Always inspect TS validity yourself anyway.
4. **Coverage dependence (optional).** Starting from an isolated run, Pynta places one co-adsorbate within 3 Å of each adsorbate or TS in every pairwise configuration. Pairs that fail to optimize prune larger configurations. An **SIDT model is then trained by active learning** on selected configurations. The talk reported about 0.05 eV MAE at about 3× the cost of the isolated run, against about 125× for enumerating everything. When fitting the polynomial coverage corrections, take them from the iterations that had converged, not from a transient spike. Spikes usually get fixed in later iterations.

## Using the results in RMG

According to the talk, Pynta outputs **RMG thermo/kinetics libraries** and **`.rms` files**.
- To use them in RMG, add them as libraries (thermo libraries, `reactionLibraries`). Follow **rmg-add-data** for placement and naming. In the RMG input, set `catalystProperties(metal=...)` or binding energies consistent with the DFT, and list the libraries in `database(...)` (see **rmg-catalysis**).
- Coverage-dependent kinetics from libraries are only used if `catalystProperties(coverageDependence=True)`.
- Simulate `.rms` output with **rmg-rms**. The talk's example of why this matters: for NH3 decomposition on Pt, coverage-dependent N2 recombination dropped the barrier from about 2.3 eV to about 0.3 eV at high N coverage, and the turnover frequency rose by more than 100×.

## Agent notes

- Periodic DFT campaigns take a long time and use cluster resources. Never launch Pynta or Fireworks jobs without explicit user approval and their cluster/MongoDB details.
- Arkane is gas-phase only. Pynta is the surface tool the talk recommends. Keeping ARC and Pynta separate is deliberate, because surface configuration enumeration dominates the problem.

**When unsure:** use Pynta's own repository README and docs (ask the user for the path or URL). Within RMG, see `rmgpy/rmg/input.py` (`catalyst_properties`) and `RMG-database/input/kinetics/libraries/Surface/` for library format examples.
