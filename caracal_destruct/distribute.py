import os
import re
import shlex
import shutil
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Union

import caracal
from caracal import log
from caracal.dispatch_crew.config_parser import basic_parser
from caracal.workers.worker_administrator import WorkerAdministrator
from ruamel.yaml import YAML

from caracal_destruct import EmptyDictDefault, EmptyListDefault, utils
from caracal_destruct.exceptions import DistributionException

yaml = YAML(typ="rt")
File = utils.File
DestructValueType = Union[str, int, float]
DestructMapType = Dict[str, Any]


@dataclass
class DestructOption:
    vars: DestructMapType
    args: List[str] = field(init=False, default_factory=list)
    workers: Dict[str, Any] = field(init=False, default_factory=dict)

    def __post_init__(self):
        workers = {}
        args = []
        for key, value in self.vars.items():
            if isinstance(value, dict):
                workers[key] = value
            else:
                args.append([key, value])

        self.args = args
        self.workers = workers


class RunMode(Enum):
    MSList: str = "mslist"
    SPWList: str = "spwlist"


class SkipMode(Enum):
    Index: str = "index"
    Label: str = "label"
    NoSkip: str = "noskip"


class MSRun:
    def __init__(
        self,
        ms: str = None,
        band: str = None,
        label: str = None,
        prefix: str = None,
        options: Dict[str, Union[DestructValueType, DestructMapType]] = None,
        imports: List[str] = None,
    ):
        self.ms = File(ms) if ms else ms
        self._band = band
        self.label = label
        self.options = options or {}
        self.imports = imports or []
        self._prefix = prefix
        self._skip = False
        self._runcmd = []

        self.split_band_option = "transform-split_field-spw"
        destruct_opts = DestructOption(self.options)
        self.workers = destruct_opts.workers
        self.cmdline_args = destruct_opts.args

        if band:
            self.band = band

    @property
    def prefix(self) -> str:
        return self._prefix

    @prefix.setter
    def prefix(self, value: str):
        self._prefix = value

    @property
    def band(self) -> str:
        return self._band

    @band.setter
    def band(self, value: str):
        self._band = value
        self.workers.update(utils.caracal_cmdline_to_dict(self.split_band_option, value))
        if self.label is None:
            self.label = "_".join(re.split(r":|~", self.band))

    @property
    def runcmd(self) -> List[str]:
        return self._runcmd

    @runcmd.setter
    def runcmd(self, value):
        self._runcmd = value

    @property
    def skip(self) -> bool:
        return self._skip

    @skip.setter
    def skip(self, value: bool):
        self._skip = value


@dataclass
class CaracalRuns:
    runs: List[MSRun]  # List of caracal run specs
    mode: RunMode  # Run mode mslist|spwlist
    all: Dict[str, Union[DestructValueType, DestructMapType]] = (
        EmptyDictDefault  # Options to passed to all caracal runs
    )
    nruns: int = field(init=False)
    bands: List[str] = field(init=False, default_factory=list)
    cmdline_args: List[str] = field(init=False, default_factory=list)
    workers: Dict[str, Any] = field(init=False, default_factory=dict)

    def __post_init__(self):
        self.nruns = len(self.runs)
        if not isinstance(self.runs[0], MSRun):
            self.runs = [MSRun(**msrun) for msrun in self.runs]

        destruct_opts = DestructOption(self.all)
        self.workers = destruct_opts.workers
        self.cmdline_args = destruct_opts.args

        self.mode = RunMode(self.mode)
        if self.mode is RunMode.SPWList:
            self.bands = [run_i.band for run_i in self.runs]
        elif self.mode is RunMode.MSList:
            for msrun in self.runs:
                if not msrun.label:
                    msrun.label = msrun.ms.stem

    def set_prefixes(self, pipeline, bands=None):
        bands = bands or self.bands
        if bands:
            if len(bands) != self.nruns:
                raise DistributionException(
                    "Number of requested bands does not match number of runs in config.caraca.runs"
                )
            else:
                set_bands = True
        else:
            set_bands = False

        for i, msrun in enumerate(self.runs):
            if set_bands:
                msrun.band = bands[i]
            # these if statements have to be in this order
            if msrun.prefix is None:
                msrun.prefix = f"{pipeline.prefix}-{msrun.label}"

        if set_bands:
            self.bands = bands

    def apply_msrun_imports(self):
        for msrun in self.runs:
            msrun_args_keys = [item[0] for item in msrun.cmdline_args]

            for imports_idx in msrun.imports:
                # Avoid overiding current run's settings
                imports_args = self.runs[imports_idx].cmdline_args

                for arg in imports_args:
                    if arg[0] not in msrun_args_keys:
                        msrun.cmdline_args.append(arg)

                msrun.workers = utils.dict_deep_merge(self.runs[imports_idx].workers, msrun.workers)


@dataclass
class DestructSchema:
    slurm: Dict[str, DestructValueType]  # Slurm runner configuration options
    caracal: CaracalRuns
    # command-line commands to run before execution.
    # For example, you can use this load modules via the 'module load' command"
    add_cmd: List[str] = EmptyListDefault

    def __post_init__(self):
        if not isinstance(self.caracal, CaracalRuns):
            self.caracal = CaracalRuns(**self.caracal)


@dataclass
class Scatter:
    caracal_runs: CaracalRuns
    caracal_config_file: Union[File, str]
    bands: List[str] = field(default_factory=list)
    spwid: int = 0
    nchan: int = None
    nband: int = None
    skiplist: List[Union[str, int]] = field(default_factory=list)
    singularity_image_dir: Union[File, str] = None
    caracal_binary: str = "caracal"
    skipmode: SkipMode = field(init=False)
    caracal_config: Dict[str, Any] = field(init=False, default_factory=dict)
    pipeline: WorkerAdministrator = field(init=False)
    caracal_run_config_files: List[File] = field(init=False)

    def __post_init__(self):
        if not isinstance(self.caracal_runs, CaracalRuns):
            self.caracal_runs = CaracalRuns(**self.caracal_runs)

        if not isinstance(self.caracal_config_file, File):
            self.caracal_config_file = File(self.caracal_config_file)

        if self.skiplist:
            if isinstance(self.skiplist[0], int):
                self.skipmode = SkipMode.Index
            elif isinstance(self.skiplist[0], str):
                self.skipmode = SkipMode.Label
            else:
                raise TypeError("The elements of the 'skiplist' have to be strings or ints")
        else:
            self.skipmode = SkipMode.NoSkip

        workers_directory = os.path.join(caracal.PCKGDIR, "workers")
        backend = "singularity"

        with open(self.caracal_config_file) as stdr:
            self.caracal_config = yaml.load(stdr)

        wa_caracal_config = utils.validate_caracal_config(self.caracal_config_file)
        wa_caracal_config["general"]["prep_workspace"] = False
        wa_caracal_config["general"]["init_notebooks"] = []
        wa_caracal_config["general"]["report_notebooks"] = []
        caracal_namespace = basic_parser().parse_args([])

        self.pipeline = WorkerAdministrator(
            wa_caracal_config,
            workers_directory,
            configFileName=self.caracal_config_file,
            singularity_image_dir=None,
            container_tech=backend,
            generate_reports=False,
            end_worker="obsconf",
            partial_init=True,
        )

        self.bands = list(self.caracal_runs.bands)
        if self.caracal_runs.mode is RunMode.SPWList:
            if self.nband:
                wsize = self.nchan // self.nband
                bw_edges = range(0, self.nchan, wsize)
                self.bands = [f"{self.spwid}:{band}~{band + wsize}" for band in bw_edges]
            elif not self.bands:
                raise RuntimeError("Both 'bands' and 'nband' are not set")

        self.caracal_runs.set_prefixes(self.pipeline, bands=self.bands)

        self.caracal_runs.apply_msrun_imports()
        self.caracal_run_config_files = []

        for run_i, msrun in enumerate(self.caracal_runs.runs):
            index_condition = self.skipmode is SkipMode.Index and run_i in self.skiplist
            label_condition = self.skipmode is SkipMode.Label and msrun.label in self.skiplist
            if index_condition or label_condition:
                msrun.skip = True
                continue

            thisrun = {
                "general": {"prefix": msrun.prefix},
                "getdata": {},
            }

            if self.caracal_runs.mode is RunMode.MSList:
                msbase = msrun.ms.basename
                msextn = msrun.ms.extension[1:]
                thisrun["getdata"]["dataid"] = [msbase]
                thisrun["getdata"]["extension"] = msextn

            thisrun.update(self.caracal_runs.workers)
            # this deep merge ensures that partial updates of nested dicts don't delete intermediate branches
            thisrun = utils.dict_deep_merge(thisrun, msrun.workers)
            non_worker_cmdline_args = []
            non_worker_cmdline_keys = []
            worker_cmdline_kwargs = {}
            for key, value in msrun.cmdline_args + self.caracal_runs.cmdline_args:
                # command-line options caracal parser namespace are sent to the command-line
                if key.replace("-", "_") in caracal_namespace:
                    if key not in non_worker_cmdline_keys:
                        non_worker_cmdline_keys.append(key)
                        non_worker_cmdline_args += [f"--{key}", value]
                # The rest (which should be worker settings) are converted to dicts are added to the config file
                else:
                    worker_cmdline_kwargs = utils.dict_deep_merge(
                        worker_cmdline_kwargs, utils.caracal_cmdline_to_dict(key, value)
                    )

            thisrun_config = utils.dict_deep_merge(self.caracal_config, thisrun)
            fname = os.path.join(self.pipeline.output, f"adestruction-{msrun.prefix}.yaml")
            with open(fname, "w") as stdw:
                yaml.dump(thisrun_config, stdw)

            log.info(f"Validating updated config for run={run_i}, label={msrun.label}")
            utils.validate_caracal_config(fname)
            # self.caracal_run_config_files.append(fname)

            runcmd = non_worker_cmdline_args + [f"--config {fname}", "-ct singularity"]
            if self.singularity_image_dir:
                runcmd += ["-sid", self.singularity_image_dir]
            # combine into a string and split using shlex for command-line friendly passing
            msrun.runcmd = [self.caracal_binary] + shlex.split(" ".join(runcmd))

    def __del__(self):
        for path in getattr(self, "caracal_run_config_files", []):
            if os.path.exists(path):
                if os.path.isfile(path):
                    try:
                        os.remove(path)
                    except OSError as e:
                        log.info(f"Error deleting file '{path}': {e}")
                elif os.path.isdir(path):
                    try:
                        shutil.rmtree(path)
                    except OSError as e:
                        log.info(f"Error deleting directory '{path}': {e}")
