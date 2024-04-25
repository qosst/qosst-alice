# Understanding the Command Line Interface

`qosst-alice` is shipped with two command line tools:

* the main command line `qosst-alice` (full documentation [here](./documentation.md));
* the command line with useful tools for Alice `qosst-alice-tools` (full documentation [here](./tools.md)).

## The main command line

The main command line allows you to start the server (as also explained in the tutorial for using `qosst-alice`). It is quite simple to use since it only takes two options: the file for the configuration and the level of verbosity.

### Configuration file

For the path of the configuration file, you can either provide an absolute or a relative path:

```{prompt} bash
qosst-alice -f /home/test/config.toml
```

```{prompt} bash
qosst-alice -f ../config.toml
```

If none is provided, it will look by default for a file name `config.toml` in the current folder.

### Verbosity level

For the level of verbosity, you can define how much logs you want with the number of `-v` provided.

For instance, if nothing is provided,

```{prompt} bash
qosst-alice
```

will print no log to the console

```{prompt} bash
qosst-alice -v
```

will print warnings and errors,

```{prompt} bash
qosst-alice -vv
```

will print infos, warnings and errors and finally

```{prompt} bash
qosst-alice -vvv
```

will print every log. Any number of `-v` superior to 3 will have the same effect.

```{note}
This only applies to the logs in the console. File logging is handled in the configuration file.
```

## The tools command line

The tools command line `qosst-alice-tools` currently provide one utility script `conversion-factor`.

### conversion-factor

This script is used to measure the conversion factor between the optical power detected at Alice's photodiode and the actual power at Alice's output. You will require a second powermeter (or photodiode) to execute this script.

The command line in itself only has the `--no-save` option which will force the script to not save anything on disk (by default the results are saved). However, upon executing the script you will be printed the special configuration object and proposed to change it *via* an interactive menu. The QOSST configuration object is not used in this case since the scheme is not the same.

Here is a picture of the proposed scheme for this experiment:

```{image} ../_static/schema_conversion_factor.png
:name: schema_conversion_factor
:align: center
```

Once the configuration is confirmed, the script will automatically change the value of the VOA, and record both optical powers to estimated the ratio. Please ensure that the value of the VOA and the power of the laser are compatible with both photodiodes.

### characterize-voa

This script can be used to characterize an electronic VOA, in particular to determine the attenuation in function of the applied voltage, to check for hysteresis, to check for stability and try modulation with on-off keying. While this script can be useful, it is not required.

The script can be launched with the command 

```{prompt} bash
qosst-alice-tools characterize-voa
```

and the configuration can be made interactively. The results are saved in a {py:class}`qosst_alice.tools.characterization_voa.CharacterizationVOAData` container containing the maximal power (*i.e* power for no attenuation), the voltages applied to get the hysteresis data and the hysteresis data (this data can also be used to get the attenuation-voltage relation), the data of the long acquisition, the voltages for the on-off keying and the output of the on-off keying. The results are saved in `voa-characterisation.qosst`.
