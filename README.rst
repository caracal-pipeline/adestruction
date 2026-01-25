============
adestruction
============

A Destruction of CARACals: Batch runners for CARACal

==============
Installation
==============

This package is available on *PYPI*

.. code-block:: bash
  
    pip install caracal-destruct

Installation from source_,
working directory where source is checked out

.. code-block:: bash
  
    pip install .


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
    -bc, --batch-config FILE        YAML file with batch configuration.
                                    Generated automatically if unspecified.
                                    [required]
    -sss, --spw-split-spec SPWID[,NCHAN][,NBAND]
                                    Comma-separated list specifying how to split
                                    the data along frequency axis into NBAND
                                    uniform partions.
    -b, --bands TEXT                CASA-style comma separated bands (or spws)
                                    to parallize the pipeline over. Example,
                                    '0:0~1023,0:1024~2048'
    -s, --skip TEXT                 Skip run(s). Comma separated list of indices
                                    (0-based), labels MS names
    -sid, --singularity_image_dir TEXT
                                    Simgularity/apptainer image directory
    --boring                        Dissable fancy logging
    -dr, --dryrun                   Do a dry run
    -ll, --log-level [debug|info|error|critical]
                                    Log level
    -v, --version                   Show the version and exit.
    --help                          Show this message and exit.

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
