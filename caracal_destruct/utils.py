import os.path
import pdb
import sys
import traceback
from typing import Union

from caracal.dispatch_crew import config_parser


class File(str):
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File '{filename}' does not exist.")
        self.filename = filename
        self.abspath = os.path.abspath(filename)
        self.isdir = os.path.isdir(filename)
        self.isfile = os.path.isfile(filename)
        self.basename = os.path.basename(filename)


def validate_caracal_config(configfile: Union[str, File]):
    argv = []
    if isinstance(configfile, File):
        configfile = File(configfile)

    try:
        parser = config_parser.config_parser()
        config, _ = parser.validate_config(configfile.filename)
        # populate parser with items from config
        parser.populate_parser(config)
        options, config = parser.update_config_from_args(config, argv)
    except config_parser.ConfigErrors as exc:
        print("{}, list of errors follows:".format(exc))
        for section, errors in exc.errors.items():
            print("  {}:".format(section))
            for err in errors:
                print("    - {}".format(err))
        sys.exit(1)  # indicate failure
    except Exception as exc:
        traceback.print_exc()
        print("Error parsing arguments or configuration: {}".format(exc))
        if options.debug:
            print("WARNING: you are running with -debug enabled, dropping you into pdb. Use Ctrl+D to exit.")
            pdb.post_mortem(sys.exc_info()[2])
        sys.exit(1)  # indicate failure

    return config
