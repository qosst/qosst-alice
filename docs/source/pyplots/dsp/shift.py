import matplotlib.pyplot as plt
from scipy import signal
import numpy as np

from qosst_core.modulation import PSKModulation
from qosst_alice.dsp import (
    generate_baseband_sequence,
    upsample,
    apply_rrc_filter,
    shift_sequence,
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

f, psd = signal.welch(data, fs=dac_rate, nperseg=2048)
mask = np.where(f > 0)[0]
fig, ax = plt.subplots(1, 1)
ax.semilogx(f[mask], psd[mask], color="black")
ax.set_xlabel("Frequency [Hz]")
ax.set_ylabel("PSD")
ax.grid()
fig.tight_layout()
