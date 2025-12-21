import logging

import caracal
import click
import stimela
from omegaconf import OmegaConf

from .slurm.run import SlurmRun
from .utils import File


@click.command()
@click.argument("config_file", type=File)
@click.option(
    "-bc",
    "--batch-config",
    "batchconfig",
    type=File,
    required=True,
    help="YAML file with batch configuration. Generated automatically if unspecified.",
)
@click.option("-nb", "--nband", type=int, help="Number of frequency bands to split data into")
@click.option(
    "-b",
    "--bands",
    type=str,
    help="CASA-style comma separated bands (or spws) to parallize the pipeline over. Overide -nb/--nband. Example, "
    "'0:0~1023,0:1024~2048'",
)
@click.option(
    "-s",
    "--skip",
    type=str,
    help="Skip run(s). Comma separated list of indices (0-based), labels MS names",
)
@click.option("-sid", "--singularity_image_dir", help="Simgularity/apptainer image directory")
@click.option("--boring", help="Dissable fancy logging", is_flag=True)
@click.option(
    "--log-level", "-ll", type=click.Choice(["debug", "info", "error", "critical"]), default="info", help="Log level"
)
def driver(config_file, nband, bands, batchconfig, skip, singularity_image_dir, boring, log_level):
    """
    A destruction of CARACals: Batch runners for CARACal

    CONFIG_FILE: CARACal configuration file
    """
    batchdict = OmegaConf.load(batchconfig.filename)

    loglevel = getattr(logging, log_level.upper())
    caracal.init_console_logging(boring=boring, debug=log_level == "debug")
    stimela.logger().setLevel(loglevel)

    if skip:
        skipus = skip.split(",")
        if skipus[0].isdigit():
            skipus = [int(num) for num in skipus]

    runit = SlurmRun(config_file, batchdict, skip=skipus, singularity_image_dir=singularity_image_dir)
    runit.scatter.set(nband=nband, bands=bands)
    runit.submit()

    return 0
