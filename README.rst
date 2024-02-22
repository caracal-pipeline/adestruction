============
adestruction
============

A Destruction of CARACals: Batch runners for CARACal

==============
Installation
==============
Installation from source_,
working directory where source is checked out

.. code-block:: bash
  
    pip install .

This package is available on *PYPI*, allowing

.. code-block:: bash
  
    pip install adestruction

=====
Usage
=====

.. code-block:: bash

    caracal-destruct --help

.. code-block:: bash

    Usage: caracal-destruct [OPTIONS] CONFIG_FILE

    A destruction of CARACals: Batch runners for CARACal

    CONFIG_FILE: CARACal configuration file

  Options:
    -bc, --batch-config FILE  YAML file with batch configuration. Generated
                              automatically if unspecified.  [required]
    -nb, --nband INTEGER      Number of frequency bands to split data into
    -b, --bands TEXT          CASA-style comma separated bands (or spws) to
                              parallize the pipeline over. Overide -nb/--nband.
                              Example, '0:0~1023,0:1024~2048'
    -s, --skip TEXT           Skip the listed steps. Specify as a comma
                              separated list of integers (starting from zero) or
                              ms names/paths.
    --help                    Show this message and exit.

=======
License
=======

This project is licensed under the GNU General Public License v3.0 - see license_ for details.

=============
Contribute
=============

Contributions are always welcome! Please ensure that you adhere to our coding
standards pep8_.

.. _license: https://github.com/caracal-pipeline/adestruction/blob/main/LICENSE
.. _pep8: https://www.python.org/dev/peps/pep-0008
.. _source: https://github.com/caracal-pipeline/adestruction
