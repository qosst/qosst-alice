# Using qosst-alice

This section will explain how to start using `qosst-alice`. This procedure is also explained in the {external+qosst:doc}`QOSST tutorial <technical/tutorial>`

## Creating the configuration file and filling it

`qosst-alice` is not shipped with a default configuration file but the default configuration file of QOSST can be generated using the following command

```{prompt} bash

qosst configuration create
```

This will create the configuration file at the `config.toml` default location. The documentation of this command can be found at the page {external+qosst-core:doc}`cli/index` of the qosst core documentation.

Once the default configuration file is created, the whole `[bob]` section can be removed. The `[alice]` and `[frame]` sections must then be completed to reach the expected behaviour, and to connect to the good hardware. Here are some link that can be useful for the documentation:

* {external+qosst:doc}`QOSST tutorial <technical/tutorial>`;
* {external+qosst-core:doc}`configuration explanation in qosst-core documentation <understanding/configuration>`;
* {external+qosst-core:doc}`filters and Zadoff-Chu explanation in qosst-core documentation <understanding/comm>`;
* {doc}`explanation on Alice's DSP <../understanding/dsp>`


## Starting the server

The server can then be started using the simple command 

```{prompt} bash
qosst-alice -f config.toml
```

It can also be useful to get the more logs by adding one or several `-v`:

```{prompt} bash
qosst-alice -f config.toml -vv
```

with the following relation:

* No `-v`: Only print errors and critical errors;
* `-v`: Same as above with warnings added;
* `-vv`: Same as above with info added;
* `-vvv`: all logs.

More information on the command line can be found {doc}`here <../cli/documentation>`.

It is recommended to start Alice's server with `-vv`. If you do so, in the absence of any client, the last line should read

```{code-block} text
DATE - qosst_alice.alice - INFO - Waiting for a client to connect.
```

If not, then something have probably gone wrong either in the configuration file or in the connection to the hardware and you should check the logs to get more information.