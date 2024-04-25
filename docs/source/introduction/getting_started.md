# Getting started

## Hardware requirements

### Operating System

The QOSST suite does not required a particular software and should work on Windows (tested), Linux (tested) and Mac (not tested).

The actual operating system requirement will come down to the hardware used for the experiment since some of them don't have interfaces with Windows.

### Python version

QOSST if officially supporting any python version 3.9 or above.

## Installing the software

There are several ways of installing the software, either by using the PyPi repositories or using the source.

### Installing the required software for Alice

To install the required software for Alice you can simply run the command

```{prompt} bash

pip install qosst-alice
```

This will automatically install `qosst-alice` (along with other required dependencies).

Alternatively, you can clone the repository at [https://github.com/qosst/qosst-alice](https://github.com/qosst/qosst-alice) and install it by source.

## Checking the version of the software

`qosst-core` will be automatically installed as it is a dependency of `qosst-alice` provides the `qosst` command from which the whole documentation can be found {external+qosst-core:doc}`here <cli/documentation>`.

You can check the version by issuing the command

```{command-output} qosst info
```

If the `qosst` command was not installed in the path, it also possible to run the following command:

```{prompt} bash
python3 -m qosst_core.commands info
```

or

```{prompt} bash
python3 -c "from qosst_core.infos import get_script_infos; print(get_script_infos())"
```

In the following we will assume that you have access to the qosst (and other) commands. If not you can replace the instructions similarly to above.

If this works and have the newest versions, you should be ready to go !
