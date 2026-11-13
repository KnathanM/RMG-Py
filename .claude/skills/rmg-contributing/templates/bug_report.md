<!-- DRAFT for the user to review. Do NOT post without explicit approval.
     Follows .github/ISSUE_TEMPLATE/bug-report.md. File it in RMG-Py (code/Arkane),
     RMG-database (data: families, libraries, groups) or RMG-website (rmg.mit.edu). -->

### Bug Description
<!-- One or two sentences: what failed, and at what stage (install / database load / reaction generation / simulation / pdep / output). -->

### How To Reproduce
1. Install mode: <Docker image tag | conda+source | conda binary>
2. Command run: `python /path/to/RMG-Py/rmg.py [flags] input.py`
3. input.py (attached below, or a minimal version that still fails)
4. The run fails after ~<time> / at iteration <N>

### Expected Behavior
<!-- e.g. "MODEL GENERATION COMPLETED", or a reaction/species that should (not) appear. -->

### Installation Information
 - OS (include version if known):
 - Installation method:
 - RMG version information:
   - RMG-Py: <Version line + git HEAD from top of RMG.log; `git describe --tags`; note any local commits/changes>
   - RMG-database: <git HEAD from top of RMG.log; note any local edits>
 - Python / Cantera / RMS(Julia) installed?:

### Additional Context
**Exact error message / traceback**
```
<paste verbatim>
```

**Last ~100 lines of RMG.log**
<details><summary>RMG.log tail</summary>

```
<paste>
```
</details>

**input.py**
<details><summary>input.py</summary>

```python
<paste>
```
</details>

<!-- Already tried: <searched closed issues for "...", re-ran after `make`, etc.> -->
