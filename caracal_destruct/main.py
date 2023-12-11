import click
import caracal
import os
import pdb
import traceback
import sys
from caracal import log
from caracal.workers.worker_administrator import WorkerAdministrator
import logging
import stimela
from caracal.dispatch_crew import config_parser
from .slurm.run import SlurmRun
import ruamel.yaml as yaml
from caracal.schema import SCHEMA_VERSION



def init_pipeline(options, config):
    # setup piping infractructure to send messages to the parent
    workers_directory = os.path.join(caracal.PCKGDIR, "workers")
    backend = config['general']['backend']
    if options.container_tech and options.container_tech != 'default':
        backend = options.container_tech

    pipeline = WorkerAdministrator(config,
               workers_directory,
               add_all_first=False, prefix=options.general_prefix,
               configFileName=options.config, singularity_image_dir=options.singularity_image_dir,
               container_tech=backend, start_worker=options.start_worker, end_worker=options.end_worker)
    return pipeline


@click.command()
@click.argument("config_file", type=str)
@click.option("-bc", "--batch-config", "batchconfig", type=click.File(),
              help="YAML file with batch configuration. Generated automatically if unspecified.")
@click.option("-nb", "--nband", type=int, default=1,
              help="Number of frequency bands to split data into")
@click.option("-b", "--bands", type=str,
              help="CASA-style comma separated bands (or spws) to parallize the pipeline over. Overide -nb/--nband. Example, '0:0~1023,0:1024~2048'")
@click.option("-s", "--skip", help="Skip the listed steps. Specify as a comma separated list of integers starting from zero.")
def driver(config_file, nband, bands, batchconfig, skip):
    """
        A destruction of CARACals: Batch runners for CARACal

        CONFIG_FILE: CARACal configuration file
    """

    argv = f"-ct singularity -c {config_file} -sw general -ew obsconf".split()
    parser = config_parser.basic_parser(argv)
    options, _ = parser.parse_known_args(argv)

    caracal.init_console_logging(boring=options.boring, debug=options.debug)
    stimela.logger().setLevel(logging.DEBUG if options.debug else logging.INFO)

    # Run caracal to get information about the input MS (-sw general -ew obsconf)

    try:
        parser = config_parser.config_parser()
        config, version = parser.validate_config(config_file)
        if version != SCHEMA_VERSION:
            log.warning("Config file {} schema version is {}, current CARACal version is {}".format(config_file,
                                    version, SCHEMA_VERSION))
            log.warning("Will try to proceed anyway, but please be advised that configuration options may have changed.")
        # populate parser with items from config
        parser.populate_parser(config)
        # reparse arguments
        caracal.log.info("Loading pipeline configuration from {}".format(config_file), extra=dict(color="GREEN"))
        options, config = parser.update_config_from_args(config, argv)
        # raise warning on schema version
    except config_parser.ConfigErrors as exc:
        log.error("{}, list of errors follows:".format(exc))
        for section, errors in exc.errors.items():
            print("  {}:".format(section))
            for err in errors:
                print("    - {}".format(err))
        sys.exit(1)  # indicate failure
    except Exception as exc:
        traceback.print_exc()
        log.error("Error parsing arguments or configuration: {}".format(exc))
        if options.debug:
            log.warning("you are running with -debug enabled, dropping you into pdb. Use Ctrl+D to exit.")
            pdb.post_mortem(sys.exc_info()[2])
        sys.exit(1)  # indicate failure

    # LOG config file to screen
    parser.log_options(config)

    # Initialise main pipeline
    pipeline = init_pipeline(options, config)

    batchdict = yaml.load(batchconfig, yaml.RoundTripLoader, version=(1, 1))

    if skip:
        skipus = [int(a) for a in skip.split(",")]
    else:
        skipus = []

    runit = SlurmRun(pipeline, config=batchdict, skip=skipus)
    # Run CARACal obsconf worker and exit. This is required to get the observation information 
    # needed to distribute the work
    runit.init_destruction()
    # Submit distrbuted jobs to Slurm
    if bands:
        bands = bands.split(",")
    runit.scatter.set(nband=nband, bands=bands)
    runit.submit()
                    
