# Characterisation of the conversion factor

The calibration part as Alice side is mainly composed by the calibration of the conversion factor. Indeed, the protocol requires to know the average number of photons per symbol {math}`\langle n \rangle` (or equivalently the modulation strength {math}`V_A=2\langle n \rangle`). This is usually done by monitoring the power using a monitoring photodiode. However this power does not directly correspond to the power at the output of Alice, since there is some attenuation between the monitoring photodiode and the output of Alice.

This issue can be taken care of by calibrating a conversion factor between the monitoring photodiode and the output of Alice. By optically short-circuiting the IQ modulator, inputting moderate powers of light and adding a power meter at the output of Alice as shown in the figure below

```{image} ../_static/schema_conversion_factor.png
:name: schema_conversion_factor
:align: center
```

it is possible to measure the conversion factor with the following formula:

```{math}
r_{conv} = \frac{P_{out}}{P_{monitoring}}
```

Moreover, as the VOA of Alice is placed before both powermeters, it's possible, by varying the attenuation on the VOA, to record several values of {math}`P_{out}` and {math}`P_{monitoring}` to obtain the value by linear regression.

This is what the `calibrate_conversion_factor` script in `qosst_alice.tools` script does. This is a standalone script, that can be launched using the `qosst-alice-tools` command as explained in more details on this {doc}`page <../cli/understanding>`.

Once the special setup has been put in place, the script can be launched with the 

```{prompt} bash
qosst-alice-tools conversion-factor
```

command line. The configuration can then be performed interactively. Once the script has finished, the value of the conversion factor is outputted and can directly be inserted into the configuration file. The default behaviour is also to save all the points for future reference, and the name of the saved file is `calibration-conversion-factor.qosst`. The data is saved as a {py:class}`qosst_alice.tools.calibrate_conversion_factor.CalibrateConversionFactorData` container and contains arrays for both powermeters, the datetime and the value of the conversion factor.
