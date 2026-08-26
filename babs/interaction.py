"""This is the main module."""

import os
import os.path as op
import warnings

import numpy as np

from babs.base import BABS
from babs.scheduler import (
    report_job_status,
    submit_array,
    submit_sacct_job,
)
from babs.utils import (
    update_submitted_job_ids,
)


class BABSInteraction(BABS):
    """Implement interactions with a BABS project - submitting jobs and checking status."""

    def babs_submit(self, count=None, submit_df=None, skip_failed=False, collect_resources=True):
        """
        This function submits jobs that don't have results yet and prints out job status.

        Parameters
        ----------
        count: int or None
            number of jobs to be submitted
            default: 1
            negative value: to submit all jobs
        submit_df: pd.DataFrame
            dataframe of jobs to be submitted
            default: None
        collect_resources: bool
            whether to also submit a job that waits for this batch to finish and
            records the resources Slurm gave each task
            default: True
        """

        # Check if there are still jobs running
        currently_running_df = self.get_currently_running_jobs_df()
        if currently_running_df.shape[0] > 0:
            raise Exception(
                'There are still jobs running. Please wait for them to finish or cancel them.'
                f' Current running jobs:\n{currently_running_df}'
            )

        # Find the rows that don't have results yet
        status_df = self.get_job_status_df()
        df_needs_submit = status_df[~status_df['has_results']].reset_index(drop=True)
        if skip_failed:
            df_needs_submit = df_needs_submit[~df_needs_submit['submitted']]

        if submit_df is not None:
            df_needs_submit = submit_df

        # only run `babs submit` when there are subjects/sessions not yet submitted
        if df_needs_submit.empty:
            print('No jobs to submit')
            return

        # If count is positive, submit the first `count` jobs
        if count is not None:
            print(f'Submitting the first {count} jobs')
            df_needs_submit = df_needs_submit.head(min(count, df_needs_submit.shape[0]))

        # We know task_id ahead of time, so we can add it to the dataframe
        df_needs_submit['task_id'] = np.arange(1, df_needs_submit.shape[0] + 1)
        # Columns to write before we know the job_id (pre-submit)
        pre_submit_cols = (
            ['sub_id', 'ses_id', 'task_id']
            if self.processing_level == 'session'
            else ['sub_id', 'task_id']
        )
        # Write the job submission dataframe to a csv file before submitting
        df_needs_submit[pre_submit_cols].to_csv(self.job_submit_path_abs, index=False)
        job_id = submit_array(
            self.analysis_path,
            self.queue,
            df_needs_submit.shape[0],
        )

        df_needs_submit['job_id'] = job_id
        # Update the job submission dataframe with the new job id
        print(f'Submitting the following jobs:\n{df_needs_submit}')
        submit_cols = (
            ['sub_id', 'ses_id', 'job_id', 'task_id']
            if self.processing_level == 'session'
            else ['sub_id', 'job_id', 'task_id']
        )
        df_needs_submit[submit_cols].to_csv(self.job_submit_path_abs, index=False)

        # Update the results df
        updated_results_df = update_submitted_job_ids(
            self.get_job_status_df(), df_needs_submit[submit_cols]
        )
        updated_results_df.to_csv(self.job_status_path_abs, index=False)

        if collect_resources:
            self._submit_resource_collection_job(job_id, df_needs_submit[submit_cols])

    def _submit_resource_collection_job(self, array_job_id, submitted_df):
        """
        Submit the job that records what resources this batch of jobs used.

        The job depends on the job array with ``afterany``, so it runs as soon as
        the whole array has finished - successfully or not - and appends one row
        per task to ``analysis/code/job_resources.csv``.

        Parameters
        ----------
        array_job_id: int
            the id of the job array that was just submitted
        submitted_df: pd.DataFrame
            the subjects (and sessions), job id and task ids of that job array
        """
        # `code/job_submit.csv` is overwritten by the next `babs submit`, which can
        # happen before this job gets to run, so give it its own copy of the mapping:
        log_path = op.join(self.analysis_path, 'logs')
        os.makedirs(log_path, exist_ok=True)
        job_submit_csv = op.join(log_path, f'job_submit_{array_job_id}.csv')
        submitted_df.to_csv(job_submit_csv, index=False)

        try:
            sacct_job_id = submit_sacct_job(
                self.analysis_path,
                self.queue,
                array_job_id,
                job_submit_csv,
            )
        except Exception as exc:
            warnings.warn(
                'Failed to submit the job that records the resources used by job '
                f'{array_job_id}; the jobs themselves were submitted fine. Error: {exc}',
                stacklevel=2,
            )
            return

        if sacct_job_id is None:
            warnings.warn(
                'This BABS project was created before `babs` could record the resources '
                'that jobs use, so no resources will be recorded for job '
                f'{array_job_id}. Re-run `babs init` to create a project that does.',
                stacklevel=2,
            )
            return

        print(
            f'Job {sacct_job_id} will record the resources used by job {array_job_id} '
            f'in {self.job_resources_path_abs} once it finishes.'
        )

    def babs_status(self):
        """
        Check job status and makes a nice report.
        """
        self._update_results_status()
        currently_running_df = self.get_currently_running_jobs_df()
        current_results_df = self.get_job_status_df()
        report_job_status(current_results_df, currently_running_df, self.analysis_path)
