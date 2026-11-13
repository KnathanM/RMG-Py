---
name: rmg-install
description: Detects how RMG (Reaction Mechanism Generator) is installed on this machine (Docker image, conda source checkout, or conda binary), finds the RMG-Py and RMG-database paths and versions, and walks through installing, updating, or repairing RMG, including the optional Julia/ReactionMechanismSimulator (RMS) add-on. Use when the user says "install RMG", "set up RMG", "is RMG installed?", "which RMG version do I have", "update RMG", "docker pull rmg", "rmg_env", "make fails", "No module named rmgpy/graph/cantera", "install RMS/Julia", "where is the RMG database", or when another RMG skill needs to know how to launch rmg.py.
---

# Installing, detecting, and updating RMG

Based on the 2025 RMG Workshop talk “RMG Installation and Update Using Docker” and RMG-Py 3.3.0.

Other RMG skills rely on this one to work out how to launch RMG. **Always detect the existing setup before you install anything.**

## 1. Detect the environment first (read-only)

Run the bundled script. It changes nothing:

```bash
bash .claude/skills/rmg-install/templates/detect_rmg_env.sh            # from the RMG-Py checkout
bash .claude/skills/rmg-install/templates/detect_rmg_env.sh /path/to/RMG-Py   # or name a specific checkout
```

If the script isn't available, these are the essential checks. Run the Python ones from inside the RMG-Py directory:

```bash
conda env list | grep -i rmg                       # is there an rmg_env?
docker images reactionmechanismgenerator/rmg       # any RMG images pulled?
docker ps -a --filter ancestor=reactionmechanismgenerator/rmg   # existing containers
ls /rmg/RMG-Py 2>/dev/null && echo "inside the Docker container"
cd $RMG_PY && conda run -n rmg_env python -c "import rmgpy; print(rmgpy.__version__, rmgpy.__file__)"
cd $RMG_PY && conda run -n rmg_env python -c "from rmgpy import settings; print(settings['database.directory'])"
git -C $RMG_PY log -1 --oneline; git -C $RMG_PY/../RMG-database log -1 --oneline
conda list -n rmg_env -f rmg                       # only non-empty for a conda *binary* install
```

How to read the results:

| Finding | Mode | How to run RMG |
|---|---|---|
| `/rmg/RMG-Py` exists | Inside Docker | `cd /rmg/RMG-Py && python rmg.py path/to/input.py`. `rmg_env` is already active. |
| Docker image/container exists on the host | Docker from the host | See §2 ("Driving the container from the host"). |
| `rmg_env` exists and rmgpy imports from `$RMG_PY/rmgpy` | Conda + source checkout | `conda activate rmg_env; python $RMG_PY/rmg.py input.py` |
| `conda list -f rmg` shows the `rmg` package | Conda binary | `conda activate rmg_env; rmg.py input.py` |
| None of the above | Not installed | Go to §2 or §3 and ask the user which mode they want. |

Facts about a source checkout that the detection should confirm:

- **`$RMG_PY`** is the RMG-Py checkout. These skills live in `RMG-Py/.claude/skills/`, so the checkout containing them is the default. If several checkouts turn up (one on `PATH`, one under `~/Software`, and so on), ask the user which one to use.
- **rmgpy may not be pip-installed.** If `python -c "import rmgpy"` fails outside the RMG-Py directory, it is imported only because `rmg.py` sits next to the `rmgpy/` folder. Always call `python $RMG_PY/rmg.py ...` by full path. For scripts, either run them from `$RMG_PY` or `export PYTHONPATH=$RMG_PY:$PYTHONPATH`.
- **`which rmg.py` finds nothing, even when RMG-Py is on `PATH`.** In this checkout `rmg.py` has no shebang and is not executable (mode 644). Adding RMG-Py to `PATH` therefore doesn't make `rmg.py input.py` work; use `python $RMG_PY/rmg.py`.
- **Database location** comes from `rmgpy/__init__.py` (`Settings`). The default is `$RMG_PY/../RMG-database/input`, so clone the two repos side by side. An `rmgrc` file overrides it. The first one found wins: `./rmgrc` in the **current working directory**, then `~/.rmg/rmgrc`, then `$RMG_PY/rmgpy/rmgrc`. Each holds one line, `database.directory : /abs/path/RMG-database/input` (template: `rmgpy/rmgrc_template`). The top of every `RMG.log` prints which source was used.
- **RMS present?** `python -c "import juliacall"` fails means RMS is not installed. Native reactors still work.
- **Dependency check:** `cd $RMG_PY && python utilities.py check-dependencies` lists Cantera, OpenBabel, pydqed, RDKit and symmetry, with versions. "symmetry Not found" only matters for QM thermo.

## 2. Docker install (recommended for new users and laptops)

Docs: `RMG-Py/documentation/source/users/rmg/installation/index.rst`. For this code version the tag is **3.3.0**. The workshop used 3.2.0. `latest` is rebuilt daily from upstream `main` and may not match this checkout.

```bash
docker pull reactionmechanismgenerator/rmg:3.3.0
# Windows: -v "C:\Users\me\myrmgfiles:/rmg/RMG-Py/myrmgfiles"    Linux/macOS: -v "$HOME/myrmgfiles:/rmg/RMG-Py/myrmgfiles"
docker run --name rmgcontainer -v "$HOME/myrmgfiles:/rmg/RMG-Py/myrmgfiles" -it reactionmechanismgenerator/rmg:3.3.0
# with Jupyter:
docker run --name rmgcontainer -v "$HOME/myrmgfiles:/rmg/RMG-Py/myrmgfiles" -it -p 8888:8888 reactionmechanismgenerator/rmg:3.3.0
#   then inside: jupyter notebook --ip 0.0.0.0 --no-browser --allow-root   -> open http://localhost:8888 (paste token)
exit                                              # leave; the container persists
docker start rmgcontainer --attach --interactive  # come back later
```

Inside the container (from `RMG-Py/Dockerfile`):

- You are `root` in `/rmg/RMG-Py`, with `(rmg_env)` active.
- The database is at `/rmg/RMG-database`.
- RMG-Py is on `PATH`.
- Julia 1.10 and RMS are pre-installed.
- Check the install with `python rmg.py --help`.

Rules:

- **Mount a subfolder** such as `/rmg/RMG-Py/myrmgfiles`. **Never mount over `/rmg`**: a bind mount hides the RMG-Py and RMG-database already in the image. That advice appeared in the workshop chat and is wrong.
- **Only files inside the mounted folder are visible on the host.** RMG writes output next to `input.py`. A job run from `examples/rmg/...` leaves its results inside the container only, so copy inputs into `myrmgfiles/<job>/` and run them there.
- **Container names are unique but persistent.** Use a new name per version or project (`rmg330`, `projectA`). Run `docker rm NAME` only after confirming with the user, because it deletes everything in the container that is outside the mount.
- **CPU and RAM limits** use Docker's own flags (e.g. `--cpus`, `--memory`); see the Docker docs.

**Driving the container from the host (for an agent).** This was not verified here; confirm it first with `docker exec rmgcontainer bash -ic 'which python'`:

```bash
docker start rmgcontainer
docker exec rmgcontainer bash -ic 'cd /rmg/RMG-Py/myrmgfiles/myjob && python /rmg/RMG-Py/rmg.py input.py'
```

**Updating Docker:** pull the new tag, then `docker run --name <newname> ...`. Old containers keep the old version.

## 3. Conda + source install (clusters, long runs, developers)

Docs: `RMG-Py/documentation/source/users/rmg/installation/anacondaDeveloper.rst`. Linux and macOS only; on Windows use WSL. **Ask the user before running these steps.** They download several GB and create a conda environment.

```bash
# 0. Miniforge (https://github.com/conda-forge/miniforge). If conda < 23.10:
conda install -n base conda-libmamba-solver && conda config --set solver libmamba
# 1. System tools: Ubuntu/Debian `sudo apt install git gcc g++ make`; Fedora `sudo dnf install git gcc gcc-c++ make`; macOS: Xcode CLT
# 2. Clone BOTH repos side by side (the database default path depends on this)
git clone https://github.com/ReactionMechanismGenerator/RMG-Py.git
git clone https://github.com/ReactionMechanismGenerator/RMG-database.git
# 3. Environment + build
cd RMG-Py
conda env create -f environment.yml            # env name rmg_env; use -n rmg_env2 for a second env
conda activate rmg_env                         # prompt must show (rmg_env), not (base)
make                                           # = check-dependencies, check-pydas, pip install --no-build-isolation -vv -e .
# 4. Test
python rmg.py --help
```

- `make` prints many compiler warnings. Ignore them unless the build actually fails.
- After `make`, rmgpy is installed in editable mode, so it imports from anywhere.
- `environment.yml` pins Python to `>=3.9,<3.12` and Cantera to `>=3.0`. Do not `conda install` random packages into `rmg_env`.
- In agent shells `conda activate` often fails. Either `eval "$(conda shell.bash hook)"` first, or call the env's interpreter directly (`$(conda info --base)/envs/rmg_env/bin/python`, or the path from `conda env list`).
- **Conda binary install** (no compiling, fixed versions only): `conda create -n rmg_env -c conda-forge -c rmg rmg` (docs: `installation/anacondaUser.rst`). Not suitable for editing code or the database.

## 4. Optional: Julia + RMS (`install_rms.sh`)

RMS is needed for these features:

- RMS reactors (`constantVIdealGasReactor`, `constantTPIdealGasReactor`, `liquidSurfaceReactor`, `constantTVLiquidReactor`).
- The transitory-edge, dead-end-radical and radical-flux model criteria.
- Arkane master-equation `method='ode'`.

In 3.3.0 Julia is loaded lazily (`rmgpy/rmg/reactionmechanismsimulator_reactors.py`, `LazyMain`), so having it installed costs nothing until it is used. The docs warn that **installing RMS can break Cantera simulations in the same env**. Keep a separate no-RMS env if the user also runs Cantera (see the rmg-simulate-cantera skill).

```bash
conda activate rmg_env            # the script installs into the ACTIVE env ($CONDA_PREFIX)
cd $RMG_PY
source install_rms.sh             # must be *sourced* (it uses `return`)
```

- The script checks for juliaup, then `julia`, then Julia 1.10, in that order. When something is missing it prints the fix and stops, for example:

  ```bash
  curl -fsSL https://install.julialang.org | sh
  # then restart the shell
  juliaup add 1.10 && juliaup default 1.10 && juliaup remove release
  ```

  **Re-run the script until it prints `ReactionMechanismSimulator is succesfully installed!`** (that spelling is the script's). It often takes about three runs.
- In the default `standard` mode it asks `Proceed with installation in '<env>'? (y/N)`. That prompt is interactive. Once the user has confirmed the env, an agent can use `RMS_INSTALLER=continuous source install_rms.sh`.
- Other options:
  - `RMS_BRANCH` (default `for_rmg`).
  - `RMS_INSTALLER=developer RMS_PATH=/path/to/ReactionMechanismSimulator.jl`.
- The script runs `conda env config vars set JULIA_*`/`PYTHON_JULIAPKG_*` and installs `pyjuliacall`. **Deactivate and reactivate `rmg_env`** afterwards. The Julia project lives in `$CONDA_PREFIX/julia_env`.
- Verify the install with `make eg8` (RMS constant-V example; output in `testing/eg8`). This first rebuilds via `make all`. A lighter check is `python -c "from juliacall import Main; Main.seval('using ReactionMechanismSimulator'); print('RMS OK')"`. The first load compiles for minutes.

## 5. Updating a source install

Ask first, and check `git status` in both repos so local edits aren't lost.

```bash
cd $RMG_PY        && git status && git pull https://github.com/ReactionMechanismGenerator/RMG-Py.git main
cd ../RMG-database && git status && git pull https://github.com/ReactionMechanismGenerator/RMG-database.git main
cd $RMG_PY && conda activate rmg_env && make        # recompile Cython after every pull
# if environment.yml changed: conda env update -f environment.yml  (or recreate the env)
# RMS (docs): julia -e 'using Pkg; Pkg.update("ReactionMechanismSimulator")'
#   install_rms.sh installs into $CONDA_PREFIX/julia_env, so --project="$PYTHON_JULIAPKG_PROJECT" is likely needed
#   (inference, not tested); re-running install_rms.sh also works
```

- Update **both** repos together. A mismatched RMG-Py and RMG-database is a classic source of load errors.
- Don't pull if the user has local, uncommitted database edits.
- Every `RMG.log` records the git commit of each repo, so you can always tell what a run used.

## 6. Hardware expectations

- A normal laptop (about 16 GB RAM, any CPU, no GPU) is enough to learn RMG and run the examples. superminimal takes about 20 s and uses about 1.2 GB.
- RMG uses whatever memory it is given. Memory is the usual limit for big runs: large Green-group models used machines with up to about 128 GB, and multi-day jobs can die from running out of memory. Run those on a cluster with a source install.
- `-n N` parallelizes only reaction generation, and it is capped by available RAM (`documentation/source/users/rmg/running.rst`).

## 7. Known errors

Full table: [reference/troubleshooting.md](reference/troubleshooting.md). The most common:

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'rmgpy'` | Run `python $RMG_PY/rmg.py` by full path, or `make` (editable install), or set `PYTHONPATH`. |
| `ImportError: No module named graph` (or another Cython module) | Not compiled for this Python. Run `make` in RMG-Py with `rmg_env` active. |
| `No module named cantera` | The env is not active. Run `conda activate rmg_env`. |
| `python: can't open file 'rmg.py'` | Wrong path to `rmg.py`. Use `$RMG_PY/rmg.py`. |
| Docker `401 Unauthorized` | Run `docker login`. |
| Docker `not found` for a tag | Check for a typo or trailing period (`rmg:3.3.0.`). |
| `requested image's platform (linux/amd64) does not match ... (linux/arm64)` | Harmless on Apple Silicon (Rosetta). |
| Mounted folder is empty after a run | The run happened outside the mount. Run inside `myrmgfiles/`. |
| `Failed to import Julia and load ReactionmechanismSimulator` | RMS reactor or feature used without RMS. Install RMS (§4) or switch to `simpleReactor`. |

## Agent safety

- Never run `conda env create`, `make`, `git pull`, `install_rms.sh`, `docker rm` or `docker pull` without telling the user what it will do and getting a yes.
- Don't edit `RMG-database` or create an `rmgrc` silently. Both change every future run.
- Report the detected mode, `$RMG_PY`, the database path and the commits back to the user before moving on.

When unsure, check:

- `RMG-Py/documentation/source/users/rmg/installation/*.rst`
- `RMG-Py/Makefile`
- `RMG-Py/install_rms.sh`
- `RMG-Py/Dockerfile`
- `RMG-Py/rmgpy/__init__.py` (settings and rmgrc)
- `RMG-Py/utilities.py`
- `RMG-Py/documentation/source/users/rmg/faq.rst`

Next step: the rmg-first-job skill.
