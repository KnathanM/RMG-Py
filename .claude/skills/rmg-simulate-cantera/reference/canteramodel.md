# `rmgpy.tools.canteramodel.Cantera` wrapper (RMG-Py 3.3.0)

This wrapper runs Cantera from RMG `Species` and `Reaction` objects. Use it when you want to change an RMG object (thermo or rate) and re-simulate without editing YAML by hand. For everything else, plain Cantera (`templates/cantera_batch.py`) is simpler.

## Tested recipe (superminimal output, Cantera 3.2)

```python
from rmgpy.chemkin import load_chemkin_file
from rmgpy.species import Species
from rmgpy.tools.canteramodel import Cantera, get_rmg_species_from_user_species, find_ignition_delay

d = "RUN/chemkin/"
spcs, rxns = load_chemkin_file(d + "chem_annotated.inp", d + "species_dictionary.txt", d + "tran.dat")
h2, o2 = Species().from_smiles("[H][H]"), Species().from_smiles("[O][O]")
m = get_rmg_species_from_user_species([h2, o2], spcs)        # match by structure, not label

job = Cantera(species_list=spcs, reaction_list=rxns, output_directory="ct_out")
job.load_model()                                             # or job.load_chemkin_model(ck_file, transport_file=...)
job.generate_conditions(reactor_type_list=["IdealGasReactor"],
                        reaction_time_list=([1.0], "s"),
                        mol_frac_list=[{m[h2]: 0.67, m[o2]: 0.33}],
                        surface_mol_frac_list=[None],        # REQUIRED for gas phase, see bug 1
                        Tlist=([1000], "K"), Plist=([1.0], "bar"))
alldata = job.simulate()           # list of (time, [T, P, species...], rxn_sens, thermo_sens) per condition
time, data, _, _ = alldata[0]
print(find_ignition_delay(time.data, data[0].data))          # data[0] is temperature; about 0.46 s here
job.plot(alldata)                  # writes ct_out/1_temperature.png, 1_pressure.png, 1_mole_fractions.png
```

Reactor types are `IdealGasReactor`, `IdealGasConstPressureReactor`, and `IdealGasConstPressureTemperatureReactor` (energy off, which is RMG's SimpleReactor). Give exactly two of `Tlist`, `Plist` and `Vlist`. Every combination of the lists becomes one condition.

For sensitivity, pass `Cantera(..., sensitive_species=[spc], thermo_SA=True)`. To perturb parameters, use `job.modify_reaction_kinetics(i, rmg_rxn)` and `job.modify_species_thermo(i, rmg_spc, use_chemkin_identifier=True)`, then call `job.refresh_model()` after any thermo change. `ipython/cantera_simulation.ipynb` shows both.

## Bugs in this version (verified by reading and running the code)

1. **No conditions are generated for gas phase.** `generate_cantera_conditions` loops over `surface_mol_frac_list` and defaults it to `[]`, so `simulate()` returns `[]`. Pass `surface_mol_frac_list=[None]`. `ipython/cantera_simulation.ipynb` passes `Tlist`/`Plist` **positionally**, which in this signature lands them in `surface_mol_frac_list`, so call by keyword. RMG's own global-uncertainty code in `rmgpy/rmg/main.py` calls it without the argument, so it hits the same problem.
2. **Surface YAML via the constructor.** `Cantera(canteraFile=..., surface_species_list=...)` hard-codes the phase name `'surface1'`, but RMG 3.3.0 writes `SURF0`. Use `job.load_chemkin_model(gas_inp, transport_file=..., surface_file=surface_inp)` instead, which detects the surface phase name from the YAML.
