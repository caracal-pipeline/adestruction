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
from .distribute import Scatter
from .slurm.run import SlurmRun
import ruamel.yaml as yaml
from caracal.schema import SCHEMA_VERSION


def get_obsconf(options, config):
    # setup piping infractructure to send messages to the parent
    workers_directory = os.path.join(caracal.PCKGDIR, "workers")
    backend = config['general']['backend']
    if options.container_tech and options.container_tech != 'default':
        backend = options.container_tech

    def __run(debug=False):
        """ Executes pipeline """
#       with stream_director(log) as director:  # stdout and stderr needs to go to the log as well -- nah
        try:
            pipeline = WorkerAdministrator(config,
                           workers_directory,
                           add_all_first=False, prefix=options.general_prefix,
                           configFileName=options.config, singularity_image_dir=options.singularity_image_dir,
                           container_tech=backend, start_worker=options.start_worker, end_worker=options.end_worker)
            pipeline.run_workers()
        except SystemExit as e:
            log.error(f"A pipeline worker initiated sys.exit({e.code}). This is likely a bug, please report.")
            log.info(f"More information can be found in the logfile at {caracal.CARACAL_LOG}")
            log.info(f"You are running version {caracal.__version__}", extra=dict(logfile_only=True))
            if debug:
                log.warning("you are running with -debug enabled, dropping you into pdb. Use Ctrl+D to exit.")
                pdb.post_mortem(sys.exc_info()[2])
            sys.exit(1) 

        except KeyboardInterrupt:
            log.error("Ctrl+C received from user, shutting down. Goodbye!")
        except Exception as exc:
            log.error(f"{exc}, [{type(exc).__name__}]", extra=dict(boldface=True))
            log.info(f"  More information can be found in the logfile at {caracal.CARACAL_LOG}")
            log.info(f"  You are running version {caracal.__version__}", extra=dict(logfile_only=True))
            for line in traceback.format_exc().splitlines():
                log.error(line, extra=dict(traceback_report=True))
            if debug:
                log.warning("you are running with -debug enabled, dropping you into pdb. Use Ctrl+D to exit.")
                pdb.post_mortem(sys.exc_info()[2])
            log.info("exiting with error code 1")
            sys.exit(1)  # indicate failure
        return pipeline

    return __run()

@click.command()
@click.argument("config_file", type=str)
@click.option("-bc", "--batch-config", "batchconfig", type=str,
              help="YAML file with batch configuration. Generated automatically if unspecified.")
@click.option("-nb", "--nband", type=int, default=1,
              help="Number of frequency bands to split data into")
@click.option("-b", "--bands", type=str,
              help="CASA-style comma separated bands (or spws) to parallize the pipeline over. Overide -nb/--nband. Example, '0:0~1023,0:1024~2048'")
def driver(config_file, nband, bands, batchconfig):
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

    obsconf = get_obsconf(options=options, config=config)
    
    scatter = Scatter(obsconf)
    scatter.set(bands or nband)
    with open(batchconfig, "r") as stdr:
        batchconfig = yaml.load(stdr, yaml.RoundTripLoader, version=(1, 1))
    runit = SlurmRun(scatter=scatter, config=batchconfig)

    runit.submit()
                    
