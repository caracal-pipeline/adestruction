import os.path
import sys
import traceback
from copy import deepcopy
from typing import Union, List, Dict

from ruamel.yaml import YAML
from caracal import log
from caracal.dispatch_crew import config_parser

yaml = YAML(typ="rt")

class File(str):
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File '{filename}' does not exist.")
        self.filename = filename
        self.abspath = os.path.abspath(filename)
        self.isdir = os.path.isdir(filename)
        self.isfile = os.path.isfile(filename)
        self.basename = os.path.basename(filename)


def validate_caracal_config(configfile: Union[str, File], args:List[str] = None):
    args = args or []
    if isinstance(configfile, File):
        configfile = configfile.filename

    try:
        parser = config_parser.config_parser()
        config, _ = parser.validate_config(configfile)
        # populate parser with items from config
        parser.populate_parser(config)
        _, config = parser.update_config_from_args(config, args)
    except config_parser.ConfigErrors as exc:
        log.info("{}, list of errors follows:".format(exc))
        for section, errors in exc.errors.items():
            log.info("  {}:".format(section))
            for err in errors:
                log.info("    - {}".format(err))
        sys.exit(1)  # indicate failure
    except Exception as exc:
        traceback.print_exc()
        log.info("Error parsing arguments or configuration: {}".format(exc))
        sys.exit(1)  # indicate failure

    return config


def caracal_cmdline_to_dict(key:str, value) -> Dict:

    keys = key.split("-")

    def traverse(keys):
        key = keys.pop(0)
        if len(keys) == 0:
            return {key: value}
        else:
            return {key: traverse(keys)}
    
    return traverse(keys)


# knicked from https://gist.github.com/angstwad/bf22d1822c38a92ec0a9?permalink_comment_id=4038517#gistcomment-4038517
def dict_deep_merge(dict_a:Dict, dict_b:Dict) -> Dict:
    result = deepcopy(dict_a)
    for bk, bv in dict_b.items():
        av = result.get(bk)
        if isinstance(av, dict) and isinstance(bv, dict):
            result[bk] = dict_deep_merge(av, bv)
        else:
            result[bk] = deepcopy(bv)
    return result


# from https://github.com/omry/omegaconf/discussions/1155#discussioncomment-8560712
def to_regular_dict(container):
    if isinstance(container, dict):
        return {k: to_regular_dict(v) for k, v in container.items()}
    elif isinstance(container, list):
        return [to_regular_dict(k) for k in container]
    else:
        return container

    