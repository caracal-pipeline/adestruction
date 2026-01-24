import pytest
from click.testing import CliRunner

from caracal_destruct import main
from caracal_destruct.distribute import DestructSchema

from . import InitTest


@pytest.fixture
def fixtures():
    return InitTest()


def test_help():
    runner = CliRunner()
    result = runner.invoke(main.driver, "--help")
    assert result.exit_code == 0


def test_spwlist(fixtures):
    caracal_config_file = fixtures.caracal_config
    destruct_config_file = fixtures.spwlist_config

    schema = DestructSchema(**fixtures.read_yaml(destruct_config_file))
    nruns = schema.caracal.nruns

    runner = CliRunner()
    result = runner.invoke(main.driver, f" --dryrun -bc {destruct_config_file} {caracal_config_file}")

    assert result.exit_code == 0
    assert "Job DRYRUN" in result.output
    assert f"run={nruns - 1}" in result.output


def test_mslist(fixtures):
    caracal_config_file = fixtures.caracal_config
    destruct_config_file = fixtures.mslist_config

    schema = DestructSchema(**fixtures.read_yaml(destruct_config_file))
    nruns = schema.caracal.nruns

    runner = CliRunner()
    result = runner.invoke(main.driver, f" --dryrun -bc {destruct_config_file} {caracal_config_file}")

    assert result.exit_code == 0
    assert "Job DRYRUN" in result.output
    assert f"run={nruns - 1}" in result.output


def test_skip(fixtures):
    caracal_config_file = fixtures.caracal_config
    destruct_config_file = fixtures.spwlist_config

    schema = DestructSchema(**fixtures.read_yaml(destruct_config_file))
    nruns = schema.caracal.nruns

    skipstring = "0,1"
    skip = [int(item) for item in skipstring.split(",")]
    runner = CliRunner()
    result = runner.invoke(
        main.driver, f" --dryrun --skip {skipstring} -bc {destruct_config_file} {caracal_config_file}"
    )

    assert result.exit_code == 0
    assert "Job DRYRUN" in result.output

    for run_i in range(nruns):
        if run_i in skip:
            assert f"run={run_i}" not in result.output
        else:
            assert f"run={run_i}" in result.output

    skipstring = "3"
    skip = [int(item) for item in skipstring.split(",")]
    result = runner.invoke(
        main.driver, f" --dryrun --skip {skipstring} -bc {destruct_config_file} {caracal_config_file}"
    )

    assert result.exit_code == 0
    assert "Job DRYRUN" in result.output

    for run_i in range(nruns):
        if run_i in skip:
            assert f"run={run_i}" not in result.output
        else:
            assert f"run={run_i}" in result.output
