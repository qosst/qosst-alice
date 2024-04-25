# Digital Signal Processing

The Digital Signal Processing (DSP) of Alice prepares the signal for its transmission in the physical domain.

The protocol that was used to define our experiment is described here, and the DSP can then be described as the following tasks:

* [Generation of symbols according to a modulation](#baseband);
* [Upsampling](#upsample);
* [Filtering](#rrc)
* [Frequency shift](#shift);
* [Frequency multiplexing of pilots](#pilots);
* [Synchronisation sequence](#zc);
* [Padding of zeros](#zeros).

In the following we describe each operation and show each function of the {py:mod}`qosst_alice.dsp` module can be used to make the DSP.

(baseband)=
## Generating the symbols and the baseband sequence

First we need to generate the baseband sequence and for this we can use the {py:func}`qosst_alice.dsp.generate_baseband_sequence` function. For this we must at least give the modulation we want to use, the variance, the size of the modulation (for discrete modulations) and the number of symbols we want.

There is a complete tutorial on the modulation on the `qosst-core` documentation, and here, for demonstrations purposes we will use a QPSK modulation (*i.e.* PSK modulation of size 4).

```{eval-rst}
.. plot:: pyplots/dsp/generate_baseband_sequence.py
    :include-source: true
    :align: center
```

```{note}
The number of symbols is low, for demonstration purposes.
```

(upsample)=
## Upsampling the data

Next we upsample the data, the can be done with the {py:func}`qosst_alice.dsp.upsample` function. This is done because we are not sending the data at the same rate as the DAC. In practice we sent the data at a rate called the symbol rate {math}`R_S` and the rate of the DAC is {math}`f_{DAC}`. The *Samples-Per-Symbol* (SPS) is defined as the ratio

```{math}
\text{SPS} = \frac{f_{DAC}}{R_S}
```

and also happen to be the upsampling factor. For instance, if we send our data at 100 MSymbols/s (or equivalently 100MBaud) and the DAC has a rate of 500MSamples/s then SPS=5.

```{eval-rst}
.. plot:: pyplots/dsp/upsample.py
    :include-source: true
    :align: center
```

(rrc)=
## Applying filter

The next step is to apply a filter. The module offers two function: {py:func}`qosst_alice.dsp.apply_rrc_filter` and {py:func}`qosst_alice.dsp.apply_rectangular_filter` but here we focus on the first, since it's more interesting for our scheme (and the one actually used).

The Raised-Cosine (RC) filter  is a filter used for pulse-shaping that minimise inter-symbols interference. Its frequency response is defined as

```{math}
H_{RC}(f) = \begin{cases}
 1,
       & |f| \leq \frac{1 - \beta}{2T_S} \\
 \frac{1}{2}\left[1 + \cos\left(\frac{\pi T_S}{\beta}\left[|f| - \frac{1 - \beta}{2T}\right]\right)\right],
       & \frac{1 - \beta}{2T_S} < |f| \leq \frac{1 + \beta}{2T_S} \\
 0,
       & \text{otherwise}
\end{cases}
```

where {math}`0\leq \beta \leq 1` is called the roll-off factor and {math}`T_S = \frac{1}{R_S}` is the inverse of the symbol rate.

The roll-off factor controls in a way the smoothness of the frequency response, and also defines the bandwidth of the resulting signal since

```{math}

B = R_S(1+\beta)

```

For instance, if {math}`R_S=100`Mbaud and {math}`\beta=0.5`, the resulting signal will have a bandwidth of 150MHz.

In our case, we apply the Raised Cosine filter in two parts: one at the transmitter and one at the receiver, by applying the Root-Raised-Cosine (RRC) filter defined as

```{math}

H_{rc}(f) = H_{rrc}(f)\cdot H_{rrc}(f)

```

```{eval-rst}
.. plot:: pyplots/dsp/rrc.py
    :include-source: true
    :align: center
```

(shift)=
## Shift the data

Next we want to shift our data in frequency to avoid low frequency noise. The only requirement for the value of {math}`f_shift` is that the signal stays in the bandwidth of the detector and {math}`f_shift>\frac{B}{2}` in case of a RF-heterodyne.

To shift the data, we can use the {py:func}`qosst_alice.dsp.frequency_shift` function.

```{eval-rst}
.. plot:: pyplots/dsp/shift.py
    :include-source: true
    :align: center
```

```{note}
We increased the number of symbols to be able to see a nice PSD.
```

(pilots)=
## Adding frequency multiplexing pilots

We then add frequency multiplexing pilots (usually 2) which are complex exponential

```{math}
    pilot = \exp\left(2\pi i t f_{pilot}\right)
```

This can be done with the {py:func}`qosst_alice.dsp.add_frequency_multiplexed_pilots` function.

```{eval-rst}
.. plot:: pyplots/dsp/pilots.py
    :include-source: true
    :align: center
```

```{note}
Please note that the values used for the ratio and power of pilots are not good and are only those one for demonstration purposes.
```

(zc)=
## Adding a synchronisation sequence

We then add a synchronisation sequence. We use a Zadoff-Chu (ZC) sequence which is a CAZAC (Constant Amplitude Zero AutoCorrelation) sequence. In our case it is defined as

```{math}
x_u(n)=\text{exp}\left(-i\frac{\pi un(n+1)}{N_{ZC}}\right)
```

for {math}`0\leq n \leq N_{ZC}` where {math}`N_{ZC}` is the length of the Zadoff-Chu sequence and {math}`u` the root of the sequence, with the requirement that {math}`\text{gcd}(u, N_{ZC}) = 1`. In practice, we choose two prime numbers to ensure this condition.

This operation can be done with the `qosst_alice.dsp.add_zc` function.

```{eval-rst}
.. plot:: pyplots/dsp/zc.py
    :include-source: true
    :align: center
```

(zeros)=
## Padding zeros

Finally, in some cases we need to pad zeros at the beginning and end of the sequence. This can be done with the `qosst_alice.dsp.add_zeros` function.

```{eval-rst}
.. plot:: pyplots/dsp/zeros.py
    :include-source: true
    :align: center
```

## The DSP function

The whole work we just did is encompassed in one, ready-to-use function, that is {py:func}`qosst_alice.dsp.dsp` and takes the whole configuration as a parameter.

Here is an example:

```{code} python

from qosst_core.configuration import Configuration
from qosst_alice.dsp import dsp_alice

config = Configuration("config.toml")

final, quantum_sequence, symbols = dsp_alice(config=config)
```

This is the code that is actually used in the {py:meth}`qosst_alice.alice.QOSSTAlice._do_dsp` method to prepare the DSP of Alice.
