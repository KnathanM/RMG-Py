#!/usr/bin/env bash
# detect_rmg_env.sh -- read-only report of how RMG is installed on this machine.
# Usage: bash detect_rmg_env.sh [path/to/RMG-Py]
# Prints: Docker or host, RMG-Py location, conda env + python, rmgpy version/import path,
# database directory, git commits, whether RMS (Julia) is usable, local Docker images.
# It changes nothing.

echo "== Context =="
if [ -f /.dockerenv ] || [ -d /rmg/RMG-Py ]; then
  echo "Looks like we are INSIDE the RMG Docker container (RMG-Py at /rmg/RMG-Py)."
  IN_DOCKER=1
else
  echo "Host machine (not inside the RMG Docker container)."
  IN_DOCKER=0
fi
echo "Active conda env: ${CONDA_DEFAULT_ENV:-<none>}"
echo "PYTHONPATH: ${PYTHONPATH:-<unset>}"

echo; echo "== Locate RMG-Py =="
# Precedence: argument > $RMG_PY > the RMG-Py checkout that contains this skill > PATH > common dirs.
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SKILL_REPO=$(cd "$SCRIPT_DIR/../../../.." 2>/dev/null && pwd)
[ -f "$SKILL_REPO/rmg.py" ] || SKILL_REPO=""
CANDIDATES=()
# rmg.py is not executable and has no shebang, so `which rmg.py` finds nothing even when it is on PATH.
IFS=: read -ra _dirs <<< "$PATH"
for d in "${_dirs[@]}"; do [ -f "$d/rmg.py" ] && [ -d "$d/rmgpy" ] && CANDIDATES+=("$(cd "$d" && pwd) (on PATH)"); done
for d in /rmg/RMG-Py "$HOME/RMG-Py" "$HOME/Code/RMG-Py" "$HOME/code/RMG-Py" "$HOME/Software/RMG-Py" "$HOME/software/RMG-Py"; do
  [ -f "$d/rmg.py" ] && CANDIDATES+=("$(cd "$d" && pwd)")
done
[ -n "$SKILL_REPO" ] && CANDIDATES+=("$SKILL_REPO (contains these skills)")
echo "Candidate RMG-Py checkouts:"; printf '  %s\n' "${CANDIDATES[@]}" | sort -u
RMG_PY_GUESS="${1:-${RMG_PY:-$SKILL_REPO}}"
if [ -z "$RMG_PY_GUESS" ] && [ ${#CANDIDATES[@]} -gt 0 ]; then RMG_PY_GUESS="${CANDIDATES[0]%% (*}"; fi
if [ $(printf '%s\n' "${CANDIDATES[@]}" | sed 's/ (.*//' | sort -u | wc -l) -gt 1 ]; then
  echo "WARNING: more than one RMG-Py checkout found. Confirm with the user which one to use."
fi
if [ -n "$RMG_PY_GUESS" ]; then
  RMG_PY=$(cd "$RMG_PY_GUESS" && pwd); echo "RMG_PY=$RMG_PY"
else
  echo "RMG-Py checkout not found (Docker-only install, or not installed)."
fi

echo; echo "== Conda environments =="
if command -v conda >/dev/null 2>&1; then
  conda env list 2>/dev/null | grep -E '^(rmg|.*rmg)' || echo "No env with 'rmg' in its name."
  ENV_PREFIX=$(conda env list 2>/dev/null | awk '$1=="rmg_env"{print $NF}')
else
  echo "conda not on PATH (may need: source ~/.bashrc, or Miniforge is not installed)."
fi
PY=""
if [ -n "$CONDA_PREFIX" ] && [ "${CONDA_DEFAULT_ENV:-}" != "base" ] && [ -x "$CONDA_PREFIX/bin/python" ]; then PY="$CONDA_PREFIX/bin/python"; fi
if [ -z "$PY" ] && [ -n "$ENV_PREFIX" ] && [ -x "$ENV_PREFIX/bin/python" ]; then PY="$ENV_PREFIX/bin/python"; fi
[ -z "$PY" ] && PY=$(command -v python)
echo "Python used for checks: $PY"

if [ -n "$RMG_PY" ] && [ -n "$PY" ]; then
  echo; echo "== rmgpy (imported from inside $RMG_PY) =="
  (cd "$RMG_PY" && "$PY" -c "import rmgpy, sys; print('rmgpy', rmgpy.__version__, 'from', rmgpy.__file__); print('python', sys.version.split()[0])" 2>&1 | tail -3)
  (cd "$RMG_PY" && "$PY" -c "from rmgpy import settings; print(settings.report())" 2>&1 | tail -3)
  echo "-- importable from outside the RMG-Py dir? (No => always call python \$RMG_PY/rmg.py)"
  (cd / && "$PY" -c "import rmgpy; print('yes:', rmgpy.__file__)" 2>&1 | tail -1)
  echo "-- compiled Cython modules present?"
  ls "$RMG_PY"/rmgpy/molecule/graph*.so 2>/dev/null | head -2 || true
  [ -z "$(ls "$RMG_PY"/rmgpy/molecule/graph*.so 2>/dev/null)" ] && echo "NO compiled graph*.so -> run 'make' in RMG-Py (with rmg_env active)"
  echo "-- Cantera / RMS (juliacall)"
  "$PY" -c "import cantera; print('cantera', cantera.__version__)" 2>&1 | tail -1
  "$PY" -c "import juliacall; print('juliacall importable: RMS may be installed (load is slow, not tested here)')" 2>&1 | tail -1
  command -v julia >/dev/null 2>&1 && echo "julia: $(julia --version 2>/dev/null) at $(command -v julia)" || echo "julia: not on PATH"

  echo; echo "== Git commits =="
  git -C "$RMG_PY" log -1 --format='RMG-Py      %h %cd %s' 2>/dev/null
  git -C "$RMG_PY" describe --tags 2>/dev/null | sed 's/^/RMG-Py describe: /'
  DB=$(cd "$RMG_PY" && "$PY" -c "from rmgpy import settings; print(settings['database.directory'])" 2>/dev/null)
  if [ -n "$DB" ]; then
    [ -d "$DB" ] && git -C "$DB/.." log -1 --format='RMG-database %h %cd %s' 2>/dev/null || echo "Database directory $DB does NOT exist"
  fi
fi

if [ "$IN_DOCKER" = 0 ]; then
  echo; echo "== Docker =="
  if command -v docker >/dev/null 2>&1; then
    docker images reactionmechanismgenerator/rmg 2>&1 | head -10
    docker ps -a --filter ancestor=reactionmechanismgenerator/rmg --format '{{.Names}}  {{.Image}}  {{.Status}}' 2>/dev/null | head -10
  else
    echo "docker not installed / not on PATH"
  fi
fi
