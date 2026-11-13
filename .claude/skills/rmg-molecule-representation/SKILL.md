---
name: rmg-molecule-representation
description: Writes, reads, and checks RMG molecule and functional-group representations, including adjacency lists (atoms, u/p/c fields, multiplicity, bond orders, isotopes, surface sites), group adjacency lists with atom types and wildcards, and SMILES/InChI. Covers the traps (triplet vs singlet O2 and CH2, "O" meaning water), resonance structures, and species()/forbidden() blocks in RMG input files. Use when the user says "write the adjacency list for", "what SMILES do I use for O2/CH2/a radical", "is this structure right", "what is this species in my log", "invalid adjacency list error", "forbid a functional group", or "add this species to my input file". It also covers decoding a structure from an RMG log or dictionary.
---

# RMG molecule representation

Based on the 2025 RMG Workshop talk “Molecule Representation in RMG” and RMG-Py 3.3.0.

RMG stores every species as a graph: atoms are nodes and bonds are edges. The **adjacency list** (adjlist) is the canonical, unambiguous form. SMILES, InChI and SMARTS are converted into it, and the conversion can surprise you. **Never trust a structure until you have round-tripped it** (see step 1). This applies especially to SMILES written by an LLM, which the presenter showed are often confidently wrong.

To find out how RMG is run on this machine (conda env or Docker, and where `$RMG_PY` is), see the `rmg-install` skill. In Docker the code is at `/rmg/RMG-Py`.

## 1. Always round-trip a structure first

Run the bundled checker on any SMILES, InChI or adjlist file before you put it in an input file or library:

```bash
python $RMG_PY/.claude/skills/rmg-molecule-representation/templates/check_structure.py "[CH2]C=CC"
python $RMG_PY/.claude/skills/rmg-molecule-representation/templates/check_structure.py my_adjlist.txt
# "No module named rmgpy": run with PYTHONPATH=$RMG_PY in the rmg_env python
```

The checker prints the formula, multiplicity, radical count, charge, SMILES, InChI, adjlist and every resonance structure. Show the user the formula and multiplicity, and confirm they are what was intended.

You can also do the same thing inline:
```python
from rmgpy.molecule import Molecule
from rmgpy.species import Species
m = Molecule(smiles='[O][O]')            # or Molecule(inchi=...), Molecule().from_adjacency_list(s)
print(m.to_adjacency_list()); print(m.multiplicity, m.get_radical_count(), m.to_smiles())
sp = Species(molecule=[m]); sp.generate_resonance_structures()
for r in sp.molecule: print(r.to_adjacency_list())
```
In Jupyter, `display(m)` draws the molecule. `str(m)` gives the SMILES.

**A SMILES or InChI cannot tell singlet and triplet apart.** Singlet and triplet CH2 both print as `[CH2]` and give the same InChI. Check the `multiplicity` and the `u`/`p` fields in the adjlist instead.

## 2. Molecule adjacency list syntax

```
CH2CHO                 <- optional label: first line, if it is a single token
multiplicity 2         <- optional integer; if omitted, RMG assumes high spin (n_radicals + 1)
1 *1 C u0 p0 c0 {2,D} {4,S} {5,S}
2    C u0 p0 c0 {1,D} {3,S} {6,S}
3    O u1 p2 c0 {2,S}
4    H u0 p0 c0 {1,S}
...
```
The fields on each atom line, in order:

| Field | Meaning |
|---|---|
| `1` | Atom index. It exists only so bonds can refer to atoms, and the order is arbitrary. A trailing `.` is allowed. |
| `*1` | Optional reaction or group label. Used in family training data and in groups. |
| `C` | Element: H, C, N, O, S, P, Si, F, Cl, Br, I, Li, He, Ne, Ar, X (surface site), e (electron). A Molecule takes the plain element only, never an atom type or a `[..]` list. |
| `u1` | Unpaired electrons, 0–4. **Required.** |
| `p2` | Lone pairs. Defaults to 0 if omitted, so write it for N, O, S and halogens. |
| `c0` | Charge: `c0`, `c+1`, `c-1` … up to ±4. Defaults to 0. |
| `i13` | Optional isotope, after the charge. Examples: `C ... i13`, `H ... i2` for D. |
| `{2,D}` | Bonds. **No spaces inside the braces.** |

Bond orders: `S` (1), `D` (2), `T` (3), `B` (1.5, benzene), `Q` (4), `vdW` (0), `H` (hydrogen bond, 0.1), `R` (reaction bond, 0.05).

The parser enforces these rules (`rmgpy/molecule/adjlist.py`). Each one has its own error:
- **Every bond is listed at both ends with the same order.** Otherwise: `Found bond between 1 and 2, but not the reverse`.
- `{2, S}` gives `Shouldn't have spaces inside braces`.
- A missing `u` field gives `Number of unpaired electrons not defined`.
- Valence: valence − bond order − u − 2p must equal the charge. Otherwise: `Invalid valency for atom C ...`. Example: forgetting the H atoms.
- Multiplicity must match the radical count. With 0–1 radicals, m = n+1. With 2, m is 1 or 3. With 3, m is 2 or 4. With 4, m is 1, 3 or 5. An atom with `u2` in a multiplicity 1 molecule gives `Violation of hund's rule`. Write a singlet carbene as `u0 p1`.
- Old-style adjlists such as `1 C 0 {2,S}`, still seen in some docs, are auto-detected. Always write the new u/p/c style.

Surface species:
- A site is element `X`. A bare site is `1 X u0 p0 c0`.
- A chemisorbed species bonds to X, e.g. `{8,S}`.
- A physisorbed species is either an X atom with no bonds or one joined with `vdW`.
- Optional `metal Pt` / `facet 111` lines are allowed.

For full catalysis input, see `rmg-catalysis`.

## 3. Group adjacency lists (database, forbidden structures)

Groups look like adjlists but allow wildcards. Parse them with `Group().from_adjacency_list(...)`, or with `adjacencyListGroup("""...""")` in an input file.
```
multiplicity [1,2]
1 *1 [Cd,CO] u0 p0 c0 {2,D}
2    R!H     ux       {1,[S,D]}
```
- Atom types or lists of them go in place of the element: `[Cd,CO]`.
- `ux`, `px`, `cx` are wildcards. Lists like `u[0,1]` are allowed.
- `multiplicity [1,2]` and `multiplicity x` are allowed.
- Bond lists like `{2,[S,D,T]}` are allowed.
- **`u` is still required on every group atom** (`ux` is fine).
- **Any `p` or `c` you leave out is a wildcard.** The talk warned that a quickly written group then matches far too much. For example, `1 *1 C u0` also matches a singlet carbene. Write `u0 p0 c0` explicitly when you mean a neutral closed-shell atom. This was checked: `1 *1 C u0` matches singlet CH2 and `1 *1 C u0 p0 c0` does not.
- Thermo groups mark the central atom with `*`. Families use `*1 *2 ...` to match the recipe.

Common atom types (full list: `rmgpy/molecule/atomtype.py`):

| Type | Meaning |
|---|---|
| `R` | any atom |
| `R!H` | any non-hydrogen atom |
| `Rx`, `Rx!H` | as above, including surface sites |
| `Val4`–`Val7` | atoms with that valence |
| `X` / `Xv` / `Xo` | any / vacant / occupied surface site |
| `Cs` | carbon with only single bonds |
| `Cd` | C=C carbon |
| `CO` | C=O carbon |
| `CS` | C=S carbon |
| `Cdd` | =C= carbon (e.g. CO2, allene) |
| `Ct` | triple-bonded carbon |
| `Cb` | benzene carbon |
| `Cbf` | fused-benzene carbon |
| `Cq` | quadruple-bonded carbon (C2) |
| `C2s` | singlet carbene carbon (CH2) |
| `C2d` | singlet carbene carbon with a double bond ([C]=C) |
| `Ca` | atomic carbon |
| `Csc`, `Cdc` … | charged carbon variants |
| `O2s` | oxygen with single bonds (water, ether, OH) |
| `O2d` | O= oxygen |
| `Oa` | atomic oxygen |
| `O4sc`, `O0sc` … | charged oxygen variants |
| `N1s`…`N5bd`, `S2s`…`S6tdc`, `P1s`…`P5bd`, `Sis`…`Siq` | N, S, P, Si types; the suffix encodes valence and bonding |
| `F1s`, `Cl1s`, `Br1s`, `I1s` | halogens |

## 4. SMILES and InChI gotchas

| You want | Write | Do **not** write |
|---|---|---|
| Triplet O2 (ground state) | `[O][O]` | `O=O`, which is singlet O2. RMG refuses it unless `generatedSpeciesConstraints(allowSingletO2=True)` is set. |
| Atomic O (triplet) | `[O]` | `O`, which is water |
| Water | `O` | |
| H atom | `[H]` | `H` |
| Triplet CH2 | `[CH2]` | |
| Singlet CH2 | adjlist `1 C u0 p1 c0 {2,S} {3,S}` + 2 H | `[CH2]`, which is always the triplet |
| Atomic C (triplet, `u2 p1`) / CH (`u1 p1`) | `[C]` / `[CH]` | RMG overrides these (`rmgpy/molecule/translator.py` `SMILES_LOOKUPS`) |
| Ar, He | `[Ar]`, `[He]` | these are also special-cased |
| Ring / aromatic | `C1CCCCC1` (cyclohexane) / `c1ccccc1` (benzene) | lowercase `c` in a chain, which does odd things |
| Branch | `CC(C)C` (isobutane) | |
| Surface site | adjlist `1 X u0 p0 c0`, or SMILES `[X]` | |
| Adsorbate | SMILES `CC*` gives ethyl bonded to X. Check the result. | |

More SMILES traps:
- `CC.X` does **not** parse in this version; it gives "Could not interpret the identifier". `CC.*` gives a physisorbed ethane.
- Output SMILES print X as `[Pt]`.
- Prefer adjlists for surface species, as all the `examples/rmg/*surface*` inputs do.

InChI (`Molecule(inchi='InChI=1S/...')`) and SMARTS are also accepted. Both lose spin information just as SMILES does.

**Reading log messages.** A bare `C` in a log may be a species *label* (from a library, possibly atomic carbon) or a *SMILES* (methane). Always find the adjlist before concluding, using `species_dictionary.txt` or `chem_annotated.inp` in the output folder. To see the structure in an error message, paste the adjlist into the checker above. The rmg.mit.edu "Molecule Search" page does the same job (see `rmg-website`).

## 5. Resonance

- A `Species` holds one or more resonance `Molecule`s. Its thermo comes from the most stable one.
- Generate them with `Species.generate_resonance_structures()` or `Molecule.generate_resonance_structures()`.
  - `[CH2]C=CC` gives `[CH2]C=CC` and `C=C[CH]C`.
  - `[O]N=O` gives `[O]N=O` and `[O-][N+]=O`.
- Symmetric cases print the same SMILES twice (allyl). Compare the adjlists instead.
- Libraries match a species through any of its resonance structures. You only need to supply one.

## 6. In an RMG input file (`rmgpy/rmg/input.py`)

```python
species(label='O2',  reactive=True,  structure=SMILES("[O][O]"))
species(label='N2',  reactive=False, structure=adjacencyList("""
1 N u0 p1 c0 {2,T}
2 N u0 p1 c0 {1,T}
"""))
species(label='CH4', structure=InChI("InChI=1S/CH4/h1H4"))   # SMARTS("...") also exists

# block one molecule
forbidden(label='cyclopropyne', structure=SMILES("C1#CC1"))
# block a whole functional group (here: every 3-membered ring)
forbidden(label='Three-member Ring', structure=adjacencyListGroup("""
1 R ux {2,[S,D,T]} {3,[S,D,T]}
2 R ux {1,[S,D,T]} {3,[S,D,T]}
3 R ux {1,[S,D,T]} {2,[S,D,T]}
"""))
```
- Labels may not contain `+`, which raises an InputError. Avoid spaces too. Labels become Chemkin names, so keep them short.
- Two `species()` with the same structure give `Species X is a duplicate of Y`.
- `reactive` defaults to True. Inert bath gases (N2, Ar, He) should be `reactive=False`.
- `species()` also takes `cut=` and `size_threshold=` for fragment-based runs, along with `fragment_adj()` / `fragment_SMILES()`.
- Library `dictionary.txt` files use the same adjlist format: a label line, then the adjlist, with a blank line between species. See `rmg-add-data`.

See `examples/rmg/commented/input.py` for annotated forms.

## 7. Agent checklist before handing a structure to RMG

1. Get the structure from a trusted source: PubChem, Wikipedia, or the user. Do not use your own memory for anything non-trivial.
2. Round-trip it (step 1). Check the formula, the multiplicity (triplet O2? singlet carbene?), the charge and the radical sites.
3. Use an adjlist whenever spin, charge or a surface site matters.
4. For groups, constrain `u`, `p` and `c` explicitly, then test them against a few molecules: `mol.is_subgraph_isomorphic(group)` should be True for the molecules you mean and False for the ones you don't.

When unsure, the source of truth is `rmgpy/molecule/adjlist.py` (parser and error messages), `rmgpy/molecule/atomtype.py` (atom types), `rmgpy/molecule/translator.py` (SMILES special cases), `rmgpy/rmg/input.py` (input-file functions) and `documentation/source/reference/molecule/adjlist.rst`.
