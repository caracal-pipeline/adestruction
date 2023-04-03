import click
import caracal
import os
import pdb
import traceback
import sys
from caracal import log
from caracal.workers import worker_administrator
import logging
import stimela
from caracal.dispatch_crew import config_parser
from .distribute import Scatter
from .slurm.run import SlurmRun
from omegaconf import OmegaConf


def get_obsconf(options, config):
    # setup piping infractructure to send messages to the parent
    workers_directory = os.path.join(caracal.pckgdir, "workers")
    backend = config['general'].get('backend', "singularity")
    if options.container_tech and options.container_tech != 'default':
        backend = options.container_tech

    def __run(debug=False):
        """ Executes pipeline """
#        with stream_director(log) as director:  # stdout and stderr needs to go to the log as well -- nah

        try:
            pipeline = worker_administrator(config,
                           workers_directory,
                           add_all_first=False, prefix=options.general_prefix,
                           configFileName=options.config, singularity_image_dir=options.singularity_image_dir,
                           container_tech=backend, start_worker="general", end_worker="obsconf")

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
    

    return __run

@click.command()
@click.argument("config", type=str)
@click.option("-bc", "--batch-config", "batchconfig", type=str,
              help="YAML file with batch configuration. Generated automatically if unspecified.")
@click.option("-nb", "--nband", type=int, default=1,
              help="Number of frequency bands to split data into")
@click.option("-b", "--bands", type=str,
              help="CASA-style comma separated bands (or spws) to parallize the pipeline over. Overide -nb/--nband. Example, '0:0~1023,0:1024~2048'")
def driver(config, nband, bands, batchconfig):
    """
        A destruction of CARACals: Batch runners for CARACal

        CONFIG: CARACal configuration file
    """

    argv = f"caracal -ct singularity -c {config}".split()
    parser = config_parser.basic_parser(argv)
    options, _ = parser.parse_known_args(argv)

    caracal.init_console_logging(boring=options.boring, debug=options.debug)
    stimela.logger().setLevel(logging.DEBUG if options.debug else logging.INFO)

    # Run caracal to get information about the input MS (-sw general -ew obsconf)
    obsconf = get_obsconf(options=options, config=config)()
    
    scatter = Scatter(obsconf)
    scatter.set(bands or nband)
    batchconfig = OmegaConf.load(batchconfig)
    runit = SlurmRun(scatter=scatter, config=batchconfig)

    runit.submit()
                    
