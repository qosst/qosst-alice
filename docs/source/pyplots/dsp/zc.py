import matplotlib.pyplot as plt
from scipy import signal
import numpy as np

from qosst_core.modulation import PSKModulation
from qosst_alice.dsp import (
    generate_baseband_sequence,
    upsample,
    apply_rrc_filter,
    shift_sequence,
    add_frequency_multiplexed_pilots,
    add_zc,
)

data = generate_baseband_sequence(
    modulation_cls=PSKModulation,
    variance=1,
    modulation_size=4,
    num_symbols=100000,
)

symbol_rate = 100e6
dac_rate = 500e6
sps = int(dac_rate / symbol_rate)

data = upsample(sequence=data, upsample_ratio=sps)

roll_off = 0.5

data = apply_rrc_filter(
    sequence=data,
    length=10 * sps + 2,
    roll_off=roll_off,
    symbol_period=1 / symbol_rate,
    sampling_rate=dac_rate,
)

f_shift = 100e6

data = shift_sequence(
    sequence=data, frequency_shift_value=f_shift, sampling_rate=dac_rate
)

pilots_frequencies = [200e6, 220e6]
pilots_amplitudes = [0.05, 0.05]

data = add_frequency_multiplexed_pilots(
    sequence=data,
    pilots_frequencies=pilots_frequencies,
    pilots_amplitudes=pilots_amplitudes,
    sampling_rate=dac_rate,
)

zc_root = 5
zc_length = 3989

data = add_zc(sequence=data, root=zc_root, length=zc_length)


fig, (ax, ax2) = plt.subplots(2, 1)
times = np.arange(len(data)) / dac_rate
ax.plot(times[:zc_length], data.real[:zc_length], color="black")
ax2.plot(times[:zc_length], data.imag[:zc_length], color="black")
ax.grid()
ax2.grid()
ax.set_xlabel("Time [s]")
ax2.set_xlabel("Time [s]")
ax.set_ylabel("Real part")
ax2.set_ylabel("Imag part")
fig.tight_layout()
