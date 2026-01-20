import os
import os.path
import shlex
from dataclasses import dataclass, field
from typing import List, Union

from caracal import log
from simple_slurm import Slurm

from caracal_destruct.distribute import DestructSchema, Scatter
from caracal_destruct.utils import File


@dataclass
class SlurmRun:
    caracal_config_file: File
    config: DestructSchema
    skiplist: List[Union[str,int]] = field(default_factory=list)
    bands: List[str] = field(default_factory=list)
    spwid: int = 0
    nchan: int = None
    nband: int = None
    singularity_image_dir: str = None
    dryrun: bool = False
    scatter: Scatter = field(init=False)
    jobs: List[int] = field(init=False, default_factory=list)

    def __post_init__(self):
        self.config = DestructSchema(**self.config)

        self.scatter = Scatter(
            caracal_runs=self.config.caracal,
            caracal_config_file=self.caracal_config_file,
            bands=self.bands,
            spwid=self.spwid,
            nchan=self.nchan,
            nband=self.nband,
            skiplist=self.skiplist,
            singularity_image_dir=self.singularity_image_dir,
            )

        logfile = f"log-adestruction-{Slurm.JOB_NAME}.txt"

        self.config.slurm.update(
            {
                "job_name": self.scatter.pipeline.prefix,
                "output": logfile,
                "error": logfile,
            }
        )

        self.slurmrun = Slurm(**self.config.slurm)
       
        self.jobs = []

    def submit(self):
        pipeline = self.scatter.pipeline
        for run_i, msrun in enumerate(self.scatter.caracal_runs.runs):
            if msrun.skip:
                log.info(f"Skipping run labelled '{msrun.label} (index: {run_i})' as requested")
                continue

            msdir = os.path.join(pipeline.msdir, msrun.label)
            outdir = os.path.join(pipeline.output, msrun.label)
            msrun.runcmd += shlex.split(f"--general-output {outdir} --general-msdir {msdir}")

            # start from a fresh runner
            self.slurmrun.reset_cmd()
            for cmd in self.config.add_cmd:
                self.slurmrun.add_cmd(cmd)

            log.info(f"Launching job using slurm. label={msrun.label} \n{self.slurmrun.__str__()}")
            log.info(f"Job I/O information:\n    msdir: {msdir}\n    outdir: {outdir}\n")
            if self.dryrun:
                log.info(f"Job DRYRUN-{msrun.label} is running: {' '.join(msrun.runcmd)} ")
            else:
                job = self.slurmrun.sbatch(*msrun.runcmd)
                log.info(f"Job {job} ({msrun.label}) is running: {' '.join(msrun.runcmd)} ")
                self.jobs.append(job)

        return self.jobs
