import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Union

from caracal_destruct import EmptyDictDefault, EmptyListDefault
from caracal_destruct.exceptions import DistributionException

DestructValueType = Union[str, int, float]


class RunMode(Enum):
    MSList: str = "mslist"
    SPWList: str = "spwlist"


class MSRun:
    def __init__(
        self,
        ms: str = None,
        band: str = None,
        label: str = None,
        prefix: str = None,
        options: Dict[str, DestructValueType] = None,
        imports: List[str] = None,
    ):
        self.ms = ms
        self._band = band
        self.label = label
        self._prefix = prefix
        self.options = options or {}
        self.imports = imports or []

        self.split_band_option = "transform-split_field-spw"

    @property
    def prefix(self) -> str:
        return self._prefix

    @prefix.setter
    def prefix(self, value):
        self._prefix = value

    @property
    def band(self) -> str:
        return self._band

    @band.setter
    def band(self, value):
        self._band = value
        if self.label is None:
            self.label = "_".join(re.split(r":|~", self.band))


@dataclass
class CaracalRuns:
    runs: List[MSRun]  # List of caracal run specs
    mode: RunMode  # Run mode mslist|spwlist
    all: Dict[str, DestructValueType] = EmptyDictDefault  # Options to passed to all caracal runs
    nruns: int = field(init=False)

    def __post_init__(self):
        self.nruns = len(self.runs)
        if not isinstance(self.runs[0], MSRun):
            self.runs = [MSRun(**msrun) for msrun in self.runs]

        self.mode = RunMode(self.mode)

    def set_prefixes(self, pipeline, bands=None):
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
    pipeline: Dict[str, Any]
    config: CaracalRuns
    obsidx: int = 0
    spwid: int = 0

    def __post_init__(self):
        if not isinstance(self.config, CaracalRuns):
            self.config = CaracalRuns(**self.config)

    def set(self, nband=None, bands=None):
        if self.config.mode is RunMode.SPWList:
            nchan = self.pipeline.nchans[self.obsidx][self.spwid]
            if nband:
                wsize = nchan // nband
                bw_edges = range(0, nchan, wsize)
                bands = [f"{self.spwid}:{band}~{band + wsize}" for band in bw_edges]
            self.config.set_prefixes(self.pipeline, bands=bands)

        self.runs = []
        for msrun in self.config.runs:
            thisrun = {}
            thisrun["general-prefix"] = msrun.prefix
            if self.config.mode is RunMode.MSList:
                msname, ext = os.path.splitext(msrun.ms)
                thisrun["getdata-dataid"] = [msname]
                thisrun["getdata-extension"] = [ext[1:]]

            # add common opts
            thisrun.update(self.config.all)
            # add imports
            for imp in msrun.imports:
                thisrun.update(self.config.runs[imp].options)
            # add fron this run
            thisrun.update(msrun.options)

            optlist = []
            for key, val in thisrun.items():
                if isinstance(val, bool):
                    val = str(val).lower()
                optlist.append(f"--{key} {val}")

            self.runs.append(optlist)
