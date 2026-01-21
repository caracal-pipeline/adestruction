import pytest
from ruamel.yaml import YAML

from caracal_destruct.distribute import CaracalRuns, DestructOption, DestructSchema, MSRun, RunMode, Scatter

from . import InitTest

yaml = YAML(typ="rt")


@pytest.fixture
def fixtures():
    return InitTest()


CONFIG_SPWList = yaml.load(
    """
add_cmd:
- module load Apptainer
slurm:
  cpus_per_task: 32
  mem: 256GB
  partition: public-cpu
  time: 2-1:00:00
caracal:
  mode: spwlist
  all:
    transform-enable: true 
    start-worker: prep
    end-worker: inspect
    transform-split_field-nthreads: 32
    flag:
      enable: true
      flag_antennas:
        enable: true
        antennas: m011,m060,m018
      flag_scan:
        enable: true
        scans: '4,16,10'
  runs:
  - label: band-01
    band: 0:0.5813~0.6985GHz
    options:
      {}      
  - label: band-02
    band: 0:0.6985~0.8157GHz
    imports: [0]
    options:
      inspect-enable: false
      crosscal:
        enable: true
  - label: band-03
    band: 0:0.8157~0.9329GHz
    imports: [0,1]
    options:
      start-worker: crosscal
      flag:
        enable: false
        antenna: 1,2
"""
)

CONFIG_MSList = yaml.load(
    """

"""
)


def test_DestructOption():
    destruct_caracal_all = yaml.load(
        """
start-worker: prep
end-worker: crosscal
prep-enable: true
inspect-enable: false
flag:
  enable: true
  flag_antennas:
    enable: true
    antennas: 1,2
general:
  prefix: mypipelinerun
"""
    )

    destruct_caracal_all = DestructOption(destruct_caracal_all)

    args = destruct_caracal_all.args
    workers = destruct_caracal_all.workers

    assert isinstance(args, list)
    assert isinstance(workers, dict)

    assert len(args) == 4
    assert len(workers.keys()) == 2

    assert "prep-enable" in [item[0] for item in args]
    assert workers["flag"]["enable"] is True
    assert workers["flag"]["flag_antennas"]["antennas"] == "1,2"


def test_MSRun():
    msrun_configs = CONFIG_SPWList["caracal"]["runs"]

    msruns = [MSRun(**item) for item in msrun_configs]

    assert msruns[0].label == "band-01"
    assert msruns[1].label == "band-02"
    assert msruns[2].label == "band-03"

    assert msruns[0].options == {}
    assert len(msruns[0].cmdline_args) == 0

    assert msruns[2].options
    assert len(msruns[2].cmdline_args) == 0
    assert "flag" in msruns[2].workers

    assert msruns[1].band == msrun_configs[1]["band"]


def test_CaracalRuns():
    config_caracal = CONFIG_SPWList["caracal"]

    crun = CaracalRuns(**config_caracal)
    assert crun.mode is RunMode.SPWList

    assert "start-worker" in [item[0] for item in crun.cmdline_args]
    assert "flag" in crun.workers

    assert crun.workers["flag"]["enable"] is True
    assert crun.workers["flag"]["flag_scan"]["scans"] == config_caracal["all"]["flag"]["flag_scan"]["scans"]

    run3_workers = dict(crun.runs[2].workers)
    crun.runs[1].cmdline_args[0][0] == "inspect-enable"
    assert not crun.runs[2].cmdline_args
    crun.apply_msrun_imports()
    assert run3_workers != crun.runs[2].workers
    crun.runs[2].cmdline_args[0][0] == "inspect-enable"


def test_DestructSchema():
    destruct = DestructSchema(**CONFIG_SPWList)

    assert "module load" in " ".join(destruct.add_cmd)
    assert destruct.slurm["cpus_per_task"] == CONFIG_SPWList["slurm"]["cpus_per_task"]
    assert isinstance(destruct.caracal, CaracalRuns)
    assert destruct.caracal.workers["flag"]["enable"] is True


def test_Scatter(fixtures):
    caracal_config_file = fixtures.caracal_config

    destruct = DestructSchema(**CONFIG_SPWList)
    bands = [irun.band for irun in destruct.caracal.runs]

    scatter = Scatter(
        destruct.caracal,
        caracal_config_file,
        bands=bands,
    )

    assert "--start-worker crosscal" in " ".join(scatter.caracal_runs.runs[2].runcmd)
    # check for duplications
    assert len(scatter.caracal_runs.runs[0].runcmd) == len(set(scatter.caracal_runs.runs[0].runcmd))
    assert len(scatter.caracal_runs.runs[1].runcmd) == len(set(scatter.caracal_runs.runs[1].runcmd))
    assert len(scatter.caracal_runs.runs[2].runcmd) == len(set(scatter.caracal_runs.runs[2].runcmd))
