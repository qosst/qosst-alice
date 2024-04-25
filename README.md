# qosst-alice

<center>

![QOSST Logo](qosst_logo_full.png)

</center>

This project is part of [QOSST](https://github.com/qosst/qosst).

## Features

`qosst-alice` is the module of QOSST in charge of the functionalities of Alice for CV-QKD. In particular it includes:

* Generation of symbols according to a given constellation of points with an associated distribution;
* Digital Signal Processing of those symbols to generate a sequence to apply on a modulator;
* Interface to apply the sequence to the hardware;
* Estimation of Alice's parameters (in particular the average number of photons per symbols);
* Alice's server code.

## Installation

The module can be installed with the following command: 

```console
pip install qosst-alice
```

It is also possible to install it directly from the github repository:

```console
pip install git+https://github.com/qosst/qosst-alice
```

It also possible to clone the repository before and install it with pip or poetry

```console
git clone https://github.com/qosst/qosst-alice
cd qosst-alice
poetry install
pip install .
```

## Documentation

The whole documentation can be found at https://qosst-alice.readthedocs.io/en/latest/

## Command line usage

A command line is shipped with the project to be able to launch Alice's server. The first step is to create a configuration file. This can be done with a command line tool shipped with the `qosst-core` package (which is a dependency of `qosst-alice`):

```console
qosst configuration create
```

This will create the default configuration file at the location `config.toml` (you change the location with the `-f` or `--file` option). For more information on the meaning of each parameter in the configuration and how to change them, check the [qosst tutorial](https://qosst.readthedocs.io/en/latest/tutorial.html).

Alice's server can then be launched with the following command: 

```console
qosst-alice -f config.toml
```

## License

As for all submodules of QOSST, `qosst-alice` is shipped under the [Gnu General Public License v3](https://www.gnu.org/licenses/gpl-3.0.html).

## Contributing

Contribution are more than welcomed, either by reporting issues or proposing merge requests. Please check the contributing section of the [QOSST](https://github.com/qosst/qosst) project fore more information.