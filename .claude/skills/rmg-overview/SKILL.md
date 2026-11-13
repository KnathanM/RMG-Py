---
name: rmg-overview
description: Orients users in the RMG ecosystem. It explains what RMG (Reaction Mechanism Generator), Arkane, RMS, ARC, T3 and the RMG-database each do, how RMG builds a mechanism with the core/edge flux-based enlargement algorithm, when RMG is (and isn't) the right tool, and which of the other RMG skills to use next. Use when the user asks "what is RMG?", "how does RMG work?", "what's the core and edge?", "should I use RMG for X?", "RMG vs Cantera/Chemkin", "what's Arkane/RMS/ARC/T3?", "where do I start with RMG?", or is new to RMG and unsure which skill applies.
---

# RMG overview and skill map

Based on the 2025 RMG Workshop talk “Introductory Remarks and RMG Overview” and RMG-Py 3.3.0.

## What RMG is

RMG automatically builds **detailed kinetic models** made of elementary reactions.

- **Inputs:** starting species, reactor conditions (T, P, composition), thermo and kinetics libraries, and tolerances.
- **What it does:**
  - enumerates possible reactions using **reaction family templates**;
  - estimates every missing thermochemistry and rate parameter;
  - decides which species and reactions matter at your conditions.
- **Output:** a mechanism in Chemkin and Cantera format (plus RMS `.rms` files), ready to simulate in Cantera, Chemkin or RMS.

**RMG builds models; Cantera/Chemkin/RMS simulate them.** RMG does run internal reactor simulations, but only to decide what to include.

Its strongest record is pyrolysis and combustion (gas phase). It also handles liquid phase (solvation corrections), heterogeneous catalysis on metal surfaces, and some polymer and electrochemistry work. Besides thermo and rates, it can estimate pressure dependence, solvation, transport and diffusivity parameters.

Estimation methods, all fast and approximate ("some guess is better than nothing"):

- **Thermo:** Benson-style **group additivity**.
- **Kinetics:** **rate rules** in hierarchical **decision trees** over the functional groups around the reacting site, one tree per reaction family.
- **Libraries:** trusted data you supply (thermo and reaction libraries, seed mechanisms) **override estimates**. "If you tell RMG that you have a good number that you trust, it will use it."

## The ecosystem

| Tool | What it does | Where |
|---|---|---|
| **RMG-Py** | Mechanism generator (Python/Cython). It includes native reactors and the analysis tools. | `RMG-Py/rmgpy`, run with `rmg.py` |
| **RMG-database** | The static data: kinetics families and trees, thermo, kinetics, solvation, transport and statmech libraries, and groups. RMG-Py code reads it; the database is plain Python-syntax files. | `RMG-database/input/` |
| **Arkane** | Turns quantum-chemistry output into thermo, TST rate coefficients and pressure-dependent networks (master equation). Ships inside RMG-Py. | `RMG-Py/arkane`, run with `Arkane.py` |
| **RMS** (ReactionMechanismSimulator.jl) | Julia reactor simulator with more reactor types and fast sensitivity analysis. Optional in 3.3.0. | Install with `install_rms.sh` |
| **ARC** | Automates quantum-chemistry calculations for species and transition states, and uses Arkane to turn them into RMG-ready data. A separate repo; not in this checkout. | github.com/ReactionMechanismGenerator |
| **T3** | Tool built on RMG that automates the iterative refinement loop described below. Separate repo; this checkout and the talks only mention it. | github.com/ReactionMechanismGenerator |
| **AutoTST, Pynta** | Automated transition-state searches (AutoTST, gas phase) and automated surface DFT workflows (Pynta). Separate repos. | — |
| **rmg.mit.edu** | Website: database browser, molecule search and online tools | — |

The three overview papers are listed in `RMG-Py/CITATIONS.bib`. Arkane's paper (2023) is listed there too.

- Gao et al., 2016, *Comput. Phys. Commun.*: RMG-Py.
- Liu et al., 2021, *J. Chem. Inf. Model.*: RMG v3.0.
- Johnson et al., 2022, *J. Chem. Inf. Model.*: RMG database and parameter estimation.

## How RMG grows a model: core and edge (plain terms)

1. **Core** = species and reactions in the model. It starts with your input species and any seed mechanisms.
2. **Edge** = candidates. RMG applies every reaction family template to the core species, and each new product species and reaction goes on the edge.
3. RMG **simulates the core** at your reactor conditions and watches the **flux** (rate of formation) into each edge species.
4. When an edge species' flux exceeds **`toleranceMoveToCore` × the characteristic core flux**, RMG interrupts the simulation and moves that species, with its reactions, into the core. The characteristic flux is the root-sum-square of core species rates (`rmgpy/solver/base.pyx`), so the threshold is relative, not absolute.
5. It generates new edge reactions for the new core species and repeats. It stops when every reactor reaches its termination criterion (time, conversion or rate ratio) without anything crossing the threshold.

Typical sizes: dozens to thousands of core species. The edge is usually at least ten times larger: a 10,000-species core may have considered about 100,000 edge species.

**Strengths and weaknesses of flux-based selection:**

- (+) It includes only species that seem important.
- (+) It needs no guess in advance about what matters. Tighten the tolerance and the model grows systematically.
- (−) **Estimation errors couple to selection.** If a rate is underestimated, or a species' enthalpy is estimated too high, that pathway may never enter the core, never shows up in sensitivity analysis, and is never fixed.
- (−) A species made slowly that later acts as a catalyst or chain-brancher can be missed. Alternative criteria exist for this (branching, transitory and others; see rmg-advanced-settings).

**Two kinds of model error:**

- *Truncation*: something left out.
- *Parametric*: wrong numbers.

The two are coupled through the point above.

**The intended workflow is a loop:**

1. Build with loose tolerances.
2. Run sensitivity and uncertainty analysis.
3. Improve the parameters that matter and are uncertain (QM via Arkane/ARC, or literature).
4. Add them as libraries.
5. **Rebuild with RMG.** The corrected numbers can change which chemistry is selected.
6. Repeat until the predictions stop changing.
7. Only then compare with experiment, tightening the tolerances as the parameters improve.

How accurate is "accurate enough"? Errors should be below about RT, so low-temperature systems need more accurate parameters.

## Is RMG the right tool?

| Situation | Recommendation |
|---|---|
| You need a detailed elementary-step mechanism for a gas-phase pyrolysis or oxidation system | Yes. This is RMG's core use case. |
| Liquid-phase oxidation, or chemistry in a solvent | Yes, with `liquidReactor` and `solvation()` (rmg-run-job, rmg-advanced-settings) |
| Catalysis on metal surfaces (Pt111, Rh111 and so on) | Yes (rmg-catalysis). Pure metals only; oxides and zeolites are not supported (workshop chat). |
| You already have a mechanism and want ignition delays, flame speeds or reactor profiles | Use Cantera or RMS to simulate it (rmg-simulate-cantera, rmg-rms) |
| You need one rate coefficient or thermo value from QM data | Arkane (arkane skill) |
| You just want an estimate for a species or reaction | RMG's estimators via scripts or the website (rmg-scripting-tools, rmg-website) |
| The chemistry needs reaction types no family covers, or mechanisms nobody has encoded | RMG cannot discover them. Add families or library reactions (rmg-add-data), or build that part by hand. |
| You want quantitative accuracy at low temperature with no refinement | Expect to iterate. Raw estimates are not good enough there. |
| Tuning a model to fit experimental data | Not RMG's job. The talks advise against tuning parameters. |

## Skill map

| Skill | Use it when |
|---|---|
| **rmg-overview** | Orientation (this skill) |
| **rmg-install** | Detecting, installing or updating RMG (Docker or conda), RMS/Julia, and fixing import or install errors |
| **rmg-first-job** | Smoke-testing an install with the superminimal example; seeing what output looks like |
| **rmg-molecule-representation** | SMILES, InChI, adjacency lists, resonance, and how RMG represents species |
| **rmg-run-job** | Writing `input.py`, running `rmg.py` with flags, monitoring `RMG.log`, reading the outputs |
| **rmg-database** | What is in RMG-database (families, trees, libraries) and how estimates are made; choosing libraries |
| **rmg-website** | Using rmg.mit.edu (database search, molecule tools, estimators) |
| **rmg-simulate-cantera** | Simulating an RMG mechanism in Cantera, and sensitivity in Cantera |
| **rmg-scripting-tools** | RMG Python API and scripts in `RMG-Py/scripts`, `rmgpy/tools`, and the IPython notebooks |
| **rmg-model-building-strategy** | Choosing tolerances, the iterate-and-refine workflow, judging whether a model has converged |
| **rmg-add-data** | Adding your own thermo or kinetics libraries, training reactions or groups |
| **rmg-contributing** | Bug reports and questions to the developers, PRs, tests |
| **arkane** | Thermo, rates and pdep networks from quantum-chemistry output |
| **rmg-rms** | RMS reactors, simulation and sensitivity with ReactionMechanismSimulator.jl |
| **rmg-pressure-dependence** | The `pressureDependence()` block, pdep networks, Chebyshev or PLOG |
| **rmg-advanced-settings** | Pruning, filtering, branching and transitory criteria, staging, constraints, memory and speed |
| **rmg-catalysis** | Surface and heterogeneous-catalysis mechanisms (`surfaceReactor`, binding energies) |
| **pynta** | Automated surface DFT workflows that feed catalysis libraries |

## Gotchas

- In the talk, "about 60 or 80" kinetics families was a rough guess. The local RMG-database (`RMG-database/input/kinetics/families/`) has **126 family directories, 34 of them surface families**. Count them yourself rather than quoting a number.
- RMG is not AI that discovers new chemistry. It only applies the chemistry encoded in its families and libraries, faster than a human could.
- The presenter's mention of a Java RMG is historical (it ended in 2016). Everything here is RMG-Py.

When unsure, check:

- `RMG-Py/documentation/source/users/rmg/introduction.rst` and `features.rst`
- `RMG-Py/documentation/source/users/rmg/input.rst`
- `RMG-Py/examples/rmg/commented/input.py`
- `RMG-Py/rmgpy/solver/base.pyx` (flux criteria)
- `RMG-Py/rmgpy/rmg/main.py`
