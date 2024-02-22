from simple_slurm import Slurm
from caracal import log
import caracal
from caracal_destruct.distribute import Scatter
from typing import List, Dict
import os
import sys
import re
import traceback
from caracal.workers.worker_administrator import WorkerAdministrator
from caracal_destruct.utils import File


class SlurmRun():
    def __init__(self, pipeline:'File' | 'WorkerAdministrator', config:Dict, skip:List):
        self.pipeline = pipeline
        self.config_caracal = config.caracal
        self.config_slurm = config.slurm
        
        self.slurm = Slurm(**self.config_slurm)
        self.skip = skip or []
        # options that apply to all runs
        self.allruns = self.config_caracal.get("all", {})
        
        self.command_line = ["caracal --general-backend singularity"]
        if isinstance(pipeline, WorkerAdministrator):
            self.pipeline = pipeline
            self.command_line += [f"--general-rawdatadir {self.pipeline.rawdatadir}"]
            self.command_line += [f"--config {self.pipeline.config_file}"]
        else:
            self.command_line += [f"--config {self.pipeline.filename}"]
        
        self.jobs = []
    
    def init_destruction(self):
        command_line = self.command_line + ["--end-worker obsconf"]
        obsconf = Slurm(**self.config_slurm)
        log.info("Running CARACal obsconf worker to get observation information. ")
        obsconf.srun(" ".join(command_line))
        log.info("CARACal obsconf files created. Ready to distribute")

        self.run_obsconf()
        self.scatter = Scatter(self.pipeline, self.config_caracal)

    def run_obsconf(self):
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
        return self.pipeline

    def submit_bands(self):
        """
        Run CARACal pipeline over specified bands using slurm
        """
        
        pipeline = self.pipeline
        if not hasattr(self, "scatter"):
            raise RuntimeError("Slurm Run scatter has not been set.")
        
        # Build caracal command
        command_line = list(self.command_line)

        self.var = "--transform-split_field-spw"
        self.values = self.scatter.bands
        self.runopts = self.scatter.runs

        for i in range(self.scatter.nband):
            band = self.values[i]
            if i in self.skip:
                log.info(f"Skipping band indexed {i}, named '{band}' as requested")
                continue
            band = self.values[i]
            runopts = self.runopts[i]
            label = "_".join(re.split(r":|~", band))
            msdir = os.path.join(pipeline.msdir, label) 
            outdir = os.path.join(pipeline.output, label)
            command = command_line + [f"--general-output {outdir} --general-msdir {msdir}"]
            if runopts:
                command += runopts
            command = " ".join(command)
            log.info(f"Launching job using slurm. SPW={band} \n{self.slurm.__str__()}")
            runstring = f"{command} {self.var} '{band}'"
            job = self.slurm.sbatch(runstring)
            log.info(f"Job {job} is running: {runstring} ")
            self.jobs.append(job)
        return self.jobs
    
    def submit_mslist(self):
        """
        Run caracal pipeline over a list of MSs
        """
        
        runopts = self.config_caracal.runs
        runidx = dict([(runopt.ms, idx) for idx, runopt in enumerate(runopts)])
        for msrun in runopts:
            job = {}
            if msrun.ms in self.skip:
                log.info(f"Skipping ms '{msrun.ms}' as requested")
                continue
            name,ext = os.path.splitext(msrun.ms)
            job["getdata-dataid"] = [name]
            job["getdata-extension"] = ext[1:]
           
            # add common options here so they can be overwritten ms-specific options 
            for key,val in self.allruns.items():
                job[key] = val
            
            # add imports from other runs
            for label in msrun.get("import", []):
                idx = runidx[label] 
                for key,val in runopts[idx]["options"].items():
                    job[key] = val
            for key,val in msrun.get("options", {}).items():
                job[key] = val
            
            # Stringify dict
            args = [f"--{key} {val}" for key,val in job.items()]
            command_line = " ".join(self.command_line + args)
            log.info(f"Launching job using slurm. ms={msrun.ms} \n{self.slurm.__str__()}")
            jobid = self.slurm.sbatch(command_line)
            self.slurm.reset_cmd()
            log.info(f"Job {jobid} is running: {command_line} ")
            self.jobs.append(jobid)
        return self.jobs
        
