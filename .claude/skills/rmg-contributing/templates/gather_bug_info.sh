#!/usr/bin/env bash
# gather_bug_info.sh -- collect the facts RMG developers need for a bug report. Read-only.
# Usage: [PY=/path/to/rmg_env/bin/python] bash gather_bug_info.sh /path/to/job_dir [/path/to/RMG-Py] > /tmp/rmg_bug_info.txt
JOB="${1:?usage: gather_bug_info.sh JOB_DIR [RMG_PY]}"
RMG_PY="${2:-${RMG_PY:-}}"
PY="${PY:-python}"   # set PY=/path/to/rmg_env/bin/python if rmg_env is not active
LOG="$JOB/RMG.log"

echo "### Environment"
echo "- OS: $(uname -srm)"; [ -f /etc/os-release ] && echo "- Distro: $(. /etc/os-release; echo "$PRETTY_NAME")"
if [ -f /.dockerenv ] || [ -d /rmg/RMG-Py ]; then echo "- Install mode: Docker container"; else echo "- Install mode: host (conda/source or binary -- confirm)"; fi
echo "- Python: $($PY --version 2>&1)  ($(command -v $PY))"
echo "- Conda env: ${CONDA_DEFAULT_ENV:-<none>}"
$PY -c "import cantera; print('- Cantera:', cantera.__version__)" 2>/dev/null
$PY -c "import juliacall" 2>/dev/null && echo "- juliacall/RMS: importable" || echo "- juliacall/RMS: not installed"

echo; echo "### Versions"
if [ -f "$LOG" ]; then
  grep -m1 "Version:" "$LOG" | sed 's/^#* */- RMG-Py /; s/ *#$//'
  awk '/The current git HEAD for RMG-Py is:/{getline a; getline b; print "- RMG-Py commit:" a " " b}
       /The current git HEAD for RMG-database is:/{getline a; getline b; print "- RMG-database commit:" a " " b}' "$LOG" | sed "s/b'//g; s/'//g; s/\t/ /g"
  grep -m1 "database.directory" "$LOG" | sed 's/^ */- /'
fi
if [ -n "$RMG_PY" ]; then
  echo "- RMG-Py describe: $(git -C "$RMG_PY" describe --tags 2>/dev/null)  local changes: $(git -C "$RMG_PY" status --porcelain 2>/dev/null | grep -v '^??' | wc -l) files"
  echo "- RMG-Py local commits not on its upstream tracking branch: $(git -C "$RMG_PY" log --oneline @{u}..HEAD 2>/dev/null | wc -l) (non-zero = custom/forked code; say so in the report)"
  echo "- RMG-database describe: $(git -C "$RMG_PY/../RMG-database" describe --tags --always 2>/dev/null)  local changes: $(git -C "$RMG_PY/../RMG-database" status --porcelain 2>/dev/null | grep -v '^??' | wc -l) files"
fi

echo; echo "### Exact error (last traceback / Error lines in RMG.log)"
if [ -f "$LOG" ]; then
  grep -n -E "Traceback|Error|Exception" "$LOG" | tail -5
else
  echo "(no RMG.log in $JOB)"
fi

echo; echo "### Last 100 lines of RMG.log"
echo '```'; [ -f "$LOG" ] && tail -n 100 "$LOG"; echo '```'

echo; echo "### input.py"
echo '```python'; [ -f "$JOB/input.py" ] && cat "$JOB/input.py" || echo "(input.py not found in $JOB -- locate the input actually used)"; echo '```'
