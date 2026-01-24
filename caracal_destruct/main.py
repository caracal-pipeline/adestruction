import logging

import caracal
import click
import stimela
from omegaconf import OmegaConf

from caracal_destruct.slurm.run import SlurmRun
from caracal_destruct.utils import File


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
@click.option(
    "-sss",
    "--spw-split-spec",
    type=str,
    metavar="SPWID[,NCHAN][,NBAND]",
    help="Comma-separated list specifying how to split the data along frequency axis into NBAND uniform partions.",
)
@click.option(
    "-b",
    "--bands",
    type=str,
    help="CASA-style comma separated bands (or spws) to parallize the pipeline over. Example, '0:0~1023,0:1024~2048'",
)
@click.option(
    "-s",
    "--skip",
    type=str,
    help="Skip run(s). Comma separated list of indices (0-based), labels MS names",
)
@click.option("-sid", "--singularity_image_dir", help="Simgularity/apptainer image directory")
@click.option("--boring", help="Dissable fancy logging", is_flag=True)
@click.option("-dr", "--dryrun", help="Do a dry run", is_flag=True)
@click.option(
    "--log-level", "-ll", type=click.Choice(["debug", "info", "error", "critical"]), default="info", help="Log level"
)
def driver(config_file, spw_split_spec, bands, batchconfig, skip, singularity_image_dir, boring, dryrun, log_level):
    """
    A destruction of CARACals: Batch runners for CARACal

    CONFIG_FILE: CARACal configuration file
    """
    batchdict = OmegaConf.load(batchconfig.filename)

    loglevel = getattr(logging, log_level.upper())
    caracal.init_console_logging(boring=boring, debug=log_level == "debug")
    stimela.logger().setLevel(loglevel)

    if skip:
        skiplist = skip.split(",")
        if skiplist[0].isdigit():
            skiplist = [int(num) for num in skiplist]
    else:
        skiplist = []

    bands = bands.split(",") if bands else []

    sss = dict(spwid=0, nchan=None, nband=None)
    sss_vals = [int(val) for val in spw_split_spec.split(",")] if spw_split_spec else []
    for i, key in enumerate(sss):
        try:
            sss[key] = int(sss_vals[i])
        except IndexError:
            # keep default value
            pass

    runit = SlurmRun(
        config_file,
        batchdict,
        skiplist=skiplist,
        bands=bands,
        spwid=sss["spwid"],
        nband=sss["nband"],
        nchan=["nchan"],
        singularity_image_dir=singularity_image_dir,
        dryrun=dryrun,
    )
    runit.submit()

    return 0
