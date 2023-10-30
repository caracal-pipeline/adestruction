from simple_slurm import Slurm
from caracal import log
import caracal
from caracal_destruct.distribute import Scatter
import os
import sys
import re
import traceback


class SlurmRun():
    def __init__(self, pipeline, config):
        self.pipeline = pipeline
        self.config_caracal = config["caracal"]
        self.config_slurm = config["slurm"]
        
        self.slurm = Slurm(**self.config_slurm)
        
        self.command_line = ["caracal --general-backend singularity"]
        self.command_line += [f"--general-rawdatadir {self.pipeline.rawdatadir}"]
        self.command_line += [f"--config {self.pipeline.config_file}"]
        
    
    def init_destruction(self):
        command_line = self.command_line + ["--end-worker obsconf"]
        obsconf = Slurm(**self.config_slurm)
        log.info("Running CARACal obsconf worker to get observation information. ")
        obsconf.srun(" ".join(command_line))
        log.info("CARACal obsconf files created. Ready to distribute")

        self.run_obsconf()
        self.scatter = Scatter(self.pipeline, self.command_line)

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

    

    def submit(self):
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
        self.jobs = []

        for i in len(self.scatter.nbands):
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
