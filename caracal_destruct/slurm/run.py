from simple_slurm import Slurm
from caracal import log as LOG
import os
import re


class SlurmRun():
    def __init__(self, scatter, config):
        self.scatter = scatter
        self.pipeline = self.scatter.pipeline
        self.config = config
        
        #self.scatter.greet()
        self.slurm = Slurm(**self.config)
    

    def submit(self):
        """
        Run CARACal pipeline over specified bands using slurm
        """
        
        pipeline = self.pipeline

        # Build caracal command
        command_line = ["caracal --general-backend singularity"]
        command_line += [f"--general-rawdatadir {pipeline.rawdatadir}"]
        command_line += [f"--config {pipeline.config_file}"]

        self.var = "--transform-split_field-spw"
        self.values = self.scatter.bands
        self.jobs = []


        for band in self.values:
            label = "_".join(re.split(r":|~", band))
            msdir = os.path.join(pipeline.msdir, label) 
            outdir = os.path.join(pipeline.output, label)
            command = command_line + [f"--general.output {outdir} --general-msdir {msdir}"]
            command = " ".join(command)
            LOG.info(f"Launching job using slurm. SPW={band} \n{self.slurm.__str__()}")
            runstring = f"{command} {self.var} '{band}'"
            job = self.slurm.sbatch(runstring)
            LOG.info(f"Job {job} is running: {runstring} ")
            self.jobs.append(job)
