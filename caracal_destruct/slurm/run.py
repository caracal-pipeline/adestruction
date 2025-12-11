from dataclasses import dataclass, field
import os.path
import os
import sys
import re
import time
import traceback
from typing import List, Dict, Union

from caracal.workers.worker_administrator import WorkerAdministrator
from caracal import log
import caracal
from omegaconf import OmegaConf
from simple_slurm import Slurm

from caracal_destruct.distribute import DestructSchema
from caracal_destruct.distribute import Scatter
from caracal_destruct.utils import File, validate_caracal_config



@dataclass
class SlurmRun():
    caracal_config_file: File
    config: DestructSchema
    skip: List[str] = None
    singularity_image_dir: str = None
    pipeline: WorkerAdministrator = field(init=False)
        
    def __post_init__(self):
        self.config = DestructSchema(**self.config)
        self.slurm_config = self.config.slurm

        self.skip = self.skip or []
        # options that apply to all runs
        self.allruns = self.config.caracal.all
        self.command_line = ["caracal --general-backend singularity"]
        self.command_line += [f"--config {self.caracal_config_file}"]
        command_line = self.command_line + ["--end-worker obsconf"]

        self.pipeline = self.get_pipeline_instance() 

        self.slurm_config.update({
            "job_name": self.pipeline.prefix,
            "output": f"log-adestruction-{Slurm.JOB_NAME}.out",
            "error": f"log-adestruction-{Slurm.JOB_NAME}.err",
        })
        self.slurmrun = Slurm(**self.slurm_config)
        self._reset_slurm()

        log.info("Running CARACal obsconf worker to get observation information. ")
        # srun is hanging for some reason, so using sbatch and using the workaround below
        jobid = self.slurmrun.sbatch(" ".join(command_line))

        max_sleep = 20/60 # obsconf worker should not take this long
        sleep_check = 5 # check every 60s
        sleep_counter = 0

        while sleep_counter <= max_sleep:
            time.sleep(sleep_check)
            sleep_counter += sleep_check
            self.slurmrun.squeue.update_squeue()
            jobdict = self.slurmrun.squeue.jobs.get(jobid, None)
            if jobdict:
                log.info(f"Job status: {jobdict['ST']}, runtime: {jobdict['TIME']}")
            else:
                continue

        log.info("CARACal obsconf files created. Ready to distribute")
        
        try:
            self.pipeline.run_workers()
        except SystemExit as e:
            log.error(f"The CARACal 'obsconf' initiated sys.exit({e.code}). This is likely a bug, please report.")
            log.info(f"More information can be found in the logfile at {caracal.CARACAL_LOG}")
            log.info(f"You are running version {caracal.__version__}", extra=dict(logfile_only=True))

        except KeyboardInterrupt:
            log.error("Ctrl+C received from user, shutting down. Goodbye!")
        except Exception as exc:
            log.error(f"{exc}, [{type(exc).__name__}]", extra=dict(boldface=True))
            log.info(f"  More information can be found in the logfile at {caracal.CARACAL_LOG}")
            log.info(f"  You are running version {caracal.__version__}", extra=dict(logfile_only=True))
            for line in traceback.format_exc().splitlines():
                log.error(line, extra=dict(traceback_report=True))
            log.info("exiting with error code 1")
            sys.exit(1)  # indicate failure

        self._reset_slurm()
        self.scatter = Scatter(self.pipeline, self.config.caracal)

        self.jobs = []

    def _reset_slurm(self):
        # remove old cmds
        self.slurmrun.reset_cmd()
        # re-add global cmds
        for cmd in self.config.add_cmd:
            self.slurmrun.add_cmd(cmd)

    def get_pipeline_instance(self):

        workers_directory = os.path.join(caracal.PCKGDIR, "workers")
        backend = "singularity"
        caracal_config_dict = validate_caracal_config(self.caracal_config_file)

        pipeline = WorkerAdministrator(caracal_config_dict,
                                       workers_directory,
                                       configFileName=self.caracal_config_file,
                                       singularity_image_dir=self.singularity_image_dir,
                                       container_tech=backend,
                                       end_worker="obsconf")

        return pipeline


    def submit(self):

        pipeline = self.pipeline
        if not hasattr(self, "scatter"):
            raise RuntimeError("Slurm Run scatter has not been set.")
        
        # Build caracal command
        command_line = list(self.command_line)

        for i,msrun in enumerate(self.config.caracal.runs):
            runopts = self.scatter.runs[i]
            # ensure a clean slurm runner
            self._reset_slurm()

            if i in self.skip:
                log.info(f"Skipping run labelled '{msrun.label}' as requested")
                continue
    
            msdir = os.path.join(pipeline.msdir, msrun.label) 
            outdir = os.path.join(pipeline.output, msrun.label)
            command = command_line + [f"--general-output {outdir} --general-msdir {msdir}"]
            if runopts:
                command += runopts
            runstring = " ".join(command)

            log.info(f"Launching job using slurm. label={msrun.label} \n{self.slurmrun.__str__()}")
            if msrun.band:
                runstring = f"{runstring} --{msrun.split_band_option} '{msrun.band}'"

            job = self.slurmrun.sbatch(runstring)
            log.info(f"Job {job} is running: {runstring} ")
            self.jobs.append(job)

        return self.jobs
    
