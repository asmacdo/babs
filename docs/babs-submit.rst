############################
``babs submit``: Submit jobs
############################

.. contents:: Table of Contents

**********************
Command-Line Arguments
**********************

.. argparse::
   :ref: babs.cli._parse_submit
   :prog: babs submit
   :nodefault:
   :nodefaultconst:

.. warning::
    Do NOT kill ``babs submit``
    while it's running! Otherwise, new job IDs may not be captured or saved into the ``job_status.csv``!


****************
Example commands
****************

Basic use
---------
If users only provide the required argument ``project_root``,
``babs submit`` will only submit one job:

.. code-block:: bash

    babs submit /path/to/my_BABS_project

Submitting a certain amount of jobs
-----------------------------------

.. code-block:: bash

    babs submit \
        /path/to/my_BABS_project \
        --count N

Change ``N`` to the number of jobs to be submitted.


Submit jobs for specific subjects (and sessions)
------------------------------------------------
For single-session datasets, select subjects with ``--select``. You can repeat the flag
or pass multiple values in one flag (argparse appends and supports nargs):

.. code-block:: bash

    babs submit \
        /path/to/my_BABS_project \
        --select sub-01 \
        --select sub-02

For multi-session datasets, include both ``sub-XX`` and ``ses-YY`` pairs:

.. code-block:: bash

    babs submit \
        /path/to/my_BABS_project \
        --select sub-01 ses-A \
        --select sub-02 ses-B

You may also pass multiple values per flag:

.. code-block:: bash

    babs submit \
        /path/to/my_BABS_project \
        --select sub-01 sub-02

.. note::
    If there are jobs currently running, ``babs submit`` will refuse to submit new jobs
    until the running jobs finish or are cancelled. Use ``babs status`` to check progress.


.. _collecting_job_resources:

*********************************
Recording the resources jobs use
*********************************

Each time ``babs submit`` submits a job array, it also submits one small job that
depends on that array with ``afterany``. That job runs as soon as the whole array
has finished -- whether the tasks succeeded, failed, ran out of time or were
cancelled -- and calls ``sacct`` to record what Slurm gave each task and what each
task actually used. The results are appended to
``/path/to/my_BABS_project/analysis/code/job_resources.csv``, one row per task.

Collecting this while it is fresh matters: Slurm's accounting database is purged on
a schedule set by the cluster's admins, so waiting until the end of a project can
mean the data is already gone.

The CSV accumulates across every batch you submit, and each row carries both what
was *requested* and what was *used*:

.. list-table::
   :header-rows: 1

   * - Column
     - What it holds
   * - ``sub_id``, ``ses_id``, ``job_id``, ``task_id``
     - Which subject (and session) the row is for.
   * - ``state``, ``exit_code``, ``exit_signal``
     - How the task ended, e.g. ``COMPLETED``, ``FAILED``, ``TIMEOUT``, ``OUT_OF_MEMORY``.
   * - ``elapsed_sec``, ``timelimit_sec``, ``queue_wait_sec``
     - Walltime used, walltime requested, and time spent waiting in the queue.
   * - ``total_cpu_sec``, ``user_cpu_sec``, ``system_cpu_sec``, ``cpu_time_sec``
     - CPU time used.
   * - ``max_rss_bytes``, ``ave_rss_bytes``, ``max_vmsize_bytes``
     - Memory used, rolled up as the maximum over the task's job steps.
   * - ``req_mem_bytes``, ``req_cpus``, ``alloc_cpus``, ``req_nodes``, ``alloc_nodes``
     - Memory and CPUs requested and allocated.
   * - ``max_disk_read_bytes``, ``max_disk_write_bytes``
     - Disk I/O.
   * - ``partition``, ``node_list``, ``cluster``, ``account``
     - Where the task ran.
   * - ``elapsed``, ``timelimit``, ``req_mem``, ``req_tres``, ``alloc_tres``
     - The unparsed ``sacct`` values, kept for reference.

The point of the file is to let you fit ``timelimit`` and ``hard_memory_limit`` to
your own data -- for example, by regressing ``elapsed_sec`` and ``max_rss_bytes``
on properties of each subject -- instead of guessing the values in the container
configuration YAML file.

.. code-block:: python

    import pandas as pd

    resources = pd.read_csv('/path/to/my_BABS_project/analysis/code/job_resources.csv')
    done = resources[resources['state'] == 'COMPLETED']
    print(done[['elapsed_sec', 'timelimit_sec', 'max_rss_bytes', 'req_mem_bytes']].describe())

To skip the accounting job for one ``babs submit`` call, pass
``--no-collect-resources``:

.. code-block:: bash

    babs submit \
        /path/to/my_BABS_project \
        --no-collect-resources

.. note::
    BABS projects created before this feature existed do not have the scripts the
    accounting job needs. ``babs submit`` will say so and submit the jobs as usual;
    re-run ``babs init`` to create a project that records its resource use.


********
See also
********
:doc:`jobs`
