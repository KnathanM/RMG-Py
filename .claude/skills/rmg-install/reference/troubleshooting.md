# RMG install troubleshooting (RMG-Py 3.3.0)

Sources: `documentation/source/users/rmg/faq.rst`, `running.rst`, `installation/anacondaDeveloper.rst`, the `Makefile`, `install_rms.sh`, `Dockerfile`, and the workshop chat. Before inventing a fix, check the closed issues on GitHub (see the rmg-contributing skill).

## Conda / source

| Symptom | Cause | Fix |
|---|---|---|
| Prompt shows `(base)` | Wrong env | `conda activate rmg_env` |
| `conda: command not found` right after installing Miniforge | Shell not refreshed | Reopen the terminal, or `source ~/.bashrc` (bash) / `source ~/.zshrc` (zsh) |
| `conda activate` fails in a non-interactive or agent shell | conda shell hook not loaded | `eval "$(conda shell.bash hook)"`, or call `<env>/bin/python` directly |
| `ImportError: No module named cantera` | Env not active | `conda activate rmg_env` (FAQ) |
| `ImportError: No module named graph` / `rmgpy.molecule.graph` | Cython not compiled, or compiled for a different Python | `cd $RMG_PY && make` with `rmg_env` active. Check that `rmgpy/molecule/graph.cpython-<pyver>-*.so` matches `python --version`. |
| `ModuleNotFoundError: No module named 'rmgpy'` when running a script | rmgpy isn't pip-installed, and the cwd isn't RMG-Py | `python $RMG_PY/rmg.py`; for scripts, `export PYTHONPATH=$RMG_PY:$PYTHONPATH`; or run `make` (editable install) |
| `python: can't open file 'rmg.py'` | Wrong `rmg.py` path | Use the absolute `$RMG_PY/rmg.py` |
| `IOError/FileNotFoundError: ... input.py` | Wrong input path | Check the path; it is relative to the cwd |
| `rmg.py input.py` → `command not found` / `Permission denied`, even with RMG-Py on `PATH` | `rmg.py` has no shebang and is mode 644 in this checkout | `python $RMG_PY/rmg.py input.py` |
| Database files not found / wrong database used | RMG-database isn't at `$RMG_PY/../RMG-database`, or a stray `rmgrc` (cwd, `~/.rmg/`, `rmgpy/`) points elsewhere | Read the `Global RMG Settings` block at the top of `RMG.log`; fix the clone location or the `rmgrc` |
| Strange database load errors after updating one repo | RMG-Py and RMG-database are out of sync | Pull both, then `make` |
| `make` prints many warnings | Normal | Ignore them unless the build ends in an error |
| `make` reports MISSING DEPENDENCIES | Env incomplete | `conda env update -f environment.yml`, or recreate the env |
| `symmetry  Not found. Please install in order to use QM.` | Optional QM dependency | Ignore it unless using `quantumMechanics()` |
| Conda solve takes forever (old conda) | Classic solver | `conda install -n base conda-libmamba-solver; conda config --set solver libmamba` |
| Licensing worries about Anaconda channels | — | Use Miniforge; `environment.yml` already lists `nodefaults`. The docs give an optional `.condarc` that forbids other channels. |
| ARM Mac build problems | Poorly tested platform | Search issues, then report it (developers asked for these reports) |
| Native Windows | Unsupported | Use WSL, or Docker |

## RMS / Julia

| Symptom | Fix |
|---|---|
| `Could not find julia via juliaup` | `curl -fsSL https://install.julialang.org \| sh`, restart the shell, `juliaup add 1.10; juliaup default 1.10; juliaup remove release`, then re-source the script |
| `Julia 1.10 is not installed. Current version is ...` | `juliaup add 1.10 && juliaup default 1.10` |
| The script exits immediately or kills the shell | It must be `source install_rms.sh`. Run with `bash`, its `return` statements fail. |
| `Aborted. Please activate the correct conda environment` | You answered no, or the wrong env is active. Activate `rmg_env` and re-run. |
| `RMS standard install error - continuing anyway` | Julia package install failed (network, precompile). Re-run. CI notes that precompilation can hang, so try `JULIA_NUM_PRECOMPILE_TASKS=1`. |
| `Failed to import Julia and load ReactionmechanismSimulator` in `RMG.log` | An RMS reactor or feature was requested but juliacall/RMS is missing. Install RMS, or use native `simpleReactor`/`liquidReactor`/`surfaceReactor`. |
| Very slow first run with Julia warnings while compiling `domain.jl` | Normal on the first load (always happened in 3.2.0; in 3.3.0 only when RMS is used). Ignore warnings that aren't errors. |
| Cantera simulations break after installing RMS | A known conflict (docs). Keep a separate env without RMS for Cantera work. |

## Docker

| Symptom | Fix |
|---|---|
| `401 Unauthorized ... failed to fetch oauth token` | `docker login` |
| `manifest ... not found` | Tag typo or trailing period. Valid tags are on Docker Hub (`3.3.0`, `3.2.0`, `latest`, ...). |
| `Cannot connect to the Docker daemon` / permission denied on `docker.sock` | Start Docker Desktop, or add the user to the `docker` group (Linux) |
| `Conflict. The container name "/rmgcontainer" is already in use` | `docker start rmgcontainer --attach --interactive`, or pick a new `--name` |
| Platform `linux/amd64` vs `linux/arm64` warning | Harmless on Apple Silicon |
| Mounted folder empty after a job | The output went next to the input file inside the container. Run jobs from inside the mount. |
| RMG-Py or database "missing" in the container | Something was mounted over `/rmg`. Recreate the container with the mount at `/rmg/RMG-Py/<subfolder>`. |
| Jupyter not reachable | The container must have been created with `-p 8888:8888`; start it with `--ip 0.0.0.0 --no-browser --allow-root` and paste the token URL |
| Need to cap CPU or RAM | Docker flags (`--cpus`, `--memory`); see the Docker docs |
