# Handoff: verify the `afterany` resource-collection job in the SLURM container

**Branch:** `claude/babs-afterany-job-collection-8lsf7f`
**Status:** feature implemented, unit-tested, pushed. **Not yet run against a real SLURM.**
**This file is a branch-only artifact — delete it before merging.**

---

## Why this file exists

BABS' pytest suite is meant to run inside the SLURM container
(`tests/pytest_in_docker.sh` → `Dockerfile_testing` → `pennlinc/slurm-docker-ci:0.14`),
because `tests/conftest.py` has a session-scoped autouse fixture that shells out to
`sacctmgr`, and because a lot of the suite needs a live scheduler.

I could not run it. The session I worked in has an egress policy that allows
`auth.docker.io` and `registry-1.docker.io` but **403s the CONNECT to
`production.cloudfront.docker.com`**, which is where Docker Hub serves image blobs.
So `docker build -f Dockerfile_testing .` cannot resolve the base image:

```
failed to resolve source metadata for docker.io/pennlinc/slurm-docker-ci:0.14:
httpReadSeeker: failed open: ... Forbidden
```

Everything below is what I verified without a scheduler, and what still needs a
container run.

## What the branch adds, in one paragraph

Every `babs submit` now also submits one small job with
`--dependency=afterany:<array_job_id> --kill-on-invalid-dep=yes`. It runs once the
whole array has finished (succeeded, failed, timed out, or cancelled), calls `sacct`,
rolls the per-step accounting rows up into one row per array task, and appends them to
`analysis/code/job_resources.csv`. The intent is to accumulate requested-vs-used
walltime and memory per subject/session so those can later be fit with a regression
instead of guessed. `--no-collect-resources` opts out.

## How to run the tests

```bash
# the project's own wrapper (note: it bind-mounts ${HOME}/projects/babs — adjust
# the -v to wherever this checkout actually lives, or run the two commands below)
./tests/pytest_in_docker.sh

# equivalent, with the mount pointed at this checkout:
docker build --platform linux/amd64 -t pennlinc/slurm-docker-ci:unstable -f Dockerfile_testing .
docker run --rm --platform linux/amd64 -h slurmctl --cap-add sys_admin --privileged \
    -v "$PWD":/babs pennlinc/slurm-docker-ci:unstable \
    pytest -sv --cov=babs /babs/tests/
```

Fastest signal first, before the full suite:

```bash
# 1. the new unit tests (no scheduler needed, but run them in-container anyway so
#    they run against the pinned pandas/numpy rather than whatever is on the host)
pytest -q /babs/tests/test_sacct_collection.py

# 2. the tests that actually submit jobs — this is where the feature is exercised
pytest -sv /babs/tests/test_babs_workflow.py /babs/tests/test_update_input_data.py

# 3. the e2e walkthrough (podman, from the repo root, outside the pytest container)
make e2e
```

## What I already verified (and how), so you don't redo it

- **46 unit tests** in `tests/test_sacct_collection.py` pass. They cover the memory
  and duration parsers, the per-task rollup, the CSV append/dedupe, the stale-mapping
  guard, unsupported-`sacct`-field dropping, the generated bash script (including
  `bash -n`), the generated sbatch command, and the `squeue` parsing fixes. `sacct` and
  `squeue` are mocked with realistic `--parsable2` output.
- **Ruff** (`check` + `format`) is clean across `babs/` and `tests/`.
- **No new failures** vs. the base branch: on the bare host I saw 22 failures in
  `test_generate_submit_script.py` / `test_utils.py`, and I confirmed by `git stash`
  that the identical 22 fail on `main` too. They look like host-environment artifacts
  (this box resolved pandas 3.0; the project pins `numpy < 2.0`). **In the container
  they should pass — if they don't, that's a separate pre-existing issue, not this
  branch.** Please confirm which it is.

## What needs the container — in priority order

### 1. Does `sacct` in that image actually report memory? (highest risk)

The whole feature is worthless if `MaxRSS` comes back empty. `sacct` only populates
`MaxRSS`/`AveRSS`/`MaxDiskRead` when job accounting gathering is switched on:

```bash
scontrol show config | grep -i JobAcctGather
```

If `JobAcctGatherType=jobacct_gather/none`, memory columns will be blank in that image
and `max_rss_bytes` will be empty in the CSV. That is a **property of the test image,
not a bug in this branch** — the collector handles blanks fine — but it means the
container cannot validate the memory half of the feature, and any test you write must
not assert on `max_rss_bytes` being populated. Say so in the PR if that's the case.
Walltime (`ElapsedRaw`, `Timelimit`) does not depend on this and should always work.

Also worth capturing, since I had to guess portably: what
`sacct --helpformat` returns in that image. The collector drops fields the local
Slurm doesn't know (`supported_fields()`), so a short field list degrades gracefully,
but I'd like to know which fields actually survived. It prints them:
`This version of sacct does not report: ...`.

### 2. Does the accounting job break the e2e walkthrough?

`tests/e2e-slurm/container/walkthrough-tests.sh:81` does:

```bash
if sacct -u "$USER" --noheader | grep -q "FAILED"; then ... exit 1
```

That greps **every** job the user has ever run — which now includes the accounting
job. If it fails for any reason, the e2e walkthrough goes red. Check it lands
`COMPLETED`. If it fails, its log is at
`analysis/logs/<3-letter-container-prefix>_sacct.o<jobid>` / `.e<jobid>`.

The same script's wait loop (`while squeue -u $USER -t RUNNING,PENDING`) will now also
wait for the accounting job to drain. That is correct, just slower by a few seconds.

### 3. Do the resource directives get accepted by that partition?

The accounting job asks for `--mem`, `--cpus-per-task=1`, `--time`, plus whatever the
container config put in `customized_text` (the CI configs put `-p all`, `--nodes=1`,
`--ntasks=1`, `--mem=2G`, `--propagate=NONE` there, and those are deliberately kept).

I made the ask **never exceed what the BIDS App itself asks for** — see `_least_of()`
in `babs/generate_submit_script.py` — so a partition that accepts the user's jobs
should accept this one. With `notebooks/eg_simbids_0-0-3_raw_mri.yaml`
(`hard_runtime_limit: "00:10:00"`) the generated script should say
`#SBATCH --time=00:10:00`, not `00:20:00`. Worth eyeballing the generated
`analysis/code/sacct_job.sh` in a bootstrapped test project to confirm.

If sbatch rejects it, `babs submit` does **not** fail — the submission is wrapped in
try/except and only warns. So check for the warning, don't just check the exit code.

### 4. Does the `squeue` parsing fix hold up?

This is the one thing on this branch that changes existing behaviour, and it is the
bug most likely to have bitten the container suite:

`tests/test_babs_workflow.py` and `test_update_input_data.py` poll the **unfiltered**
`squeue_to_pandas()` in a wait loop. Before this branch, every row was an array task
(`<job>_<task>`). Now the accounting job is always in the queue as a bare `<job>`, and
the old code did `df['job_id'].str.split('_').str[1].astype(int)` → **`ValueError:
cannot convert float NaN to integer`**. I reproduced that directly.

`babs/scheduler.py::squeue_to_pandas` now coerces `job_id` to str, parses both parts
with `errors='coerce'`, and **drops rows that are not array tasks** (BABS only ever
tracks array tasks; `request_all_job_status` always filters by an array job id anyway).
There is a second edge case in there: when *every* row is a non-array job — which is
exactly the state right after the array drains and only the collector is left —
pandas infers the column as int64 and the `.str` accessor raises. Both cases have
regression tests (`test_squeue_ignores_the_accounting_job`,
`test_squeue_with_only_the_accounting_job_left`).

**Consequence to sanity-check in the container:** because non-array rows are dropped,
those wait loops now exit as soon as the *array* finishes, while the collector may
still be pending. I believe that is safe — the next `babs submit` only checks the
previous array's job id, and each collector reads its own snapshot at
`analysis/logs/job_submit_<array_job_id>.csv` rather than the shared
`code/job_submit.csv` — but it is worth confirming that `babs merge` and the second
`babs submit` in `test_babs_workflow.py` still behave.

### 5. Smaller things

- `babs check-setup` should still pass. I deliberately did **not** add
  `sacct_job.sh` / `sacct_job.py` / `submit_sacct_job_template.yaml` to the
  required-files list in `babs/check_setup.py`, so that projects bootstrapped by an
  older babs don't hard-fail. Reasonable people could disagree; flag it in review if
  you think check-setup should assert on them.
- Confirm `analysis/code/job_resources.csv` is actually created, has the subject and
  session ids filled in, and is git-ignored (bootstrap adds it to `.gitignore`).
- The collector retries 5×30s if the accounting DB hasn't caught up. If a container
  config has a very short `hard_runtime_limit`, that 2.5-minute budget could outlive
  the job's own walltime. Not a problem for any config in the repo, but if you see the
  collector killed by TIMEOUT, that's the reason — lower `--n-retries` in
  `babs/templates/sacct_job.sh.jinja2`.

## Where things live

| File | What it is |
|---|---|
| `babs/template_sacct_job.py` | The collector. Stdlib-only, copied into `analysis/code/sacct_job.py` by `babs init`. |
| `babs/templates/sacct_job.sh.jinja2` | The sbatch script that invokes it. |
| `babs/templates/sacct_job_submit.yaml.jinja2` | The `sbatch` command template, with `${array_job_id}` / `${job_submit_csv}` placeholders. |
| `babs/generate_submit_script.py` | `generate_sacct_submit_script()`, `SACCT_JOB_RESOURCES`, `_least_of()` and the two slurm-value parsers. |
| `babs/container.py` | `generate_bash_sacct_job()`, `generate_sacct_job_submit_template()`. |
| `babs/bootstrap.py` | Generates the above at `babs init`, `datalad save`s them, gitignores the CSV. |
| `babs/scheduler.py` | `submit_sacct_job()`, plus the `squeue_to_pandas` fix. |
| `babs/interaction.py` | `_submit_resource_collection_job()`, called at the end of `babs_submit`. |
| `babs/cli.py` | `--collect-resources` / `--no-collect-resources`. |
| `babs/base.py` | `job_resources_path_abs`. |
| `docs/babs-submit.rst` | User docs, including the CSV's column reference. |
| `tests/test_sacct_collection.py` | The 46 unit tests. |

## Design decisions you may want to revisit

- **Stdlib-only collector.** No pandas, so it runs in whatever environment
  `script_preamble` sets up on the compute node. Costs some verbosity in parsing.
- **The rollup is the non-obvious part.** Requested resources are on the allocation
  row (`123_4`); used memory is only on the step rows (`123_4.batch`, `.extern`). The
  collector merges the allocation row and takes the max over steps. `.extern` must not
  win. Pending array ranges (`123_[5-8]`) are skipped.
- **Per-batch mapping snapshot** at `analysis/logs/job_submit_<job_id>.csv`, because
  `code/job_submit.csv` gets overwritten by the next `babs submit` and the collector
  may not have run yet. The collector also verifies the `job_id` matches before using
  the mapping, so a stale file can't mislabel subjects — it just leaves them blank.
- **Old projects degrade, they don't break.** No template on disk → `submit_sacct_job`
  returns `None` → `babs submit` warns and carries on.
- **`--kill-on-invalid-dep=yes`** so a collector doesn't linger forever if its array
  never runs.
