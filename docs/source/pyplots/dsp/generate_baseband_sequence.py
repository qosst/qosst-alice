import matplotlib.pyplot as plt

from qosst_core.modulation import PSKModulation
from qosst_alice.dsp import generate_baseband_sequence

data = generate_baseband_sequence(
    modulation_cls=PSKModulation,
    variance=1,
    modulation_size=4,
    num_symbols=50,
)

fig, axs = plt.subplots(2, 2)
gs = axs[0, 1].get_gridspec()
for ax in axs[0:, -1]:
    ax.remove()
ax3 = fig.add_subplot(gs[0:, -1])
(ax, _), (ax2, _) = axs
ax.plot(data.real, color="black")
ax2.plot(data.imag, color="black")
ax3.scatter(data.real, data.imag, color="black")
ax3.set_aspect("equal")
ax.grid()
ax2.grid()
ax3.grid()
ax.set_ylabel("Real part")
ax2.set_ylabel("Imag part")
ax3.set_xlabel("Real part")
ax3.set_ylabel("Imag part")
fig.tight_layout()
