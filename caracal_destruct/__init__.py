import os
import subprocess
from dataclasses import field
from importlib.metadata import PackageNotFoundError, version

from caracal_destruct import exceptions

DistributionException = exceptions.DistributionException

# Data class defaults
EmptyDictDefault = field(default_factory=dict)
EmptyListDefault = field(default_factory=list)


def report_version():
    """Get version from package metadata, git tags, or git commit hash."""
    try:
        __version__ = version("caracal-destruct")
    except PackageNotFoundError:
        __version__ = "dev"
    
    path = os.path.dirname(os.path.abspath(__file__))
    
    # Try git describe first (tags)
    def _git_output(cmd):
        try:
            return subprocess.check_output(
                f"cd {path}; {cmd}", shell=True, stderr=subprocess.STDOUT
            ).rstrip().decode()
        except subprocess.CalledProcessError:
            return None
    
    # Try git tags
    result = _git_output("git describe --tags")
    if result and "fatal" not in result:
        return result
    
    # Try git commit hash
    result = _git_output("git rev-parse --short HEAD")
    if result and "fatal" not in result:
        return f"{__version__}-{result}"
    
    # Fallback to package version
    return __version__


__version__ = VERSION = report_version()
