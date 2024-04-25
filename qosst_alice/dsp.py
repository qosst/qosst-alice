# qosst-alice - Alice module of the Quantum Open Software for Secure Transmissions.
# Copyright (C) 2021-2024 Yoann Piétri

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
This module holds two different things :

* First the dsp function, that takes a configuration object as a parameter, and render directly the signals to be sent to the modulator
* And other functions that will be called by the dsp function and that will take individual (i.e. not configuration object) parameters.
"""
import logging
from typing import Tuple, Type

import numpy as np
from scipy import signal

from qosst_core.utils import QOSSTPath
from qosst_core.configuration import Configuration
from qosst_core.modulation.modulation import Modulation
from qosst_core.comm.zc import zcsequence
from qosst_core.comm.filters import root_raised_cosine_filter, rect_filter
from qosst_core.configuration.exceptions import InvalidConfiguration

logger = logging.getLogger(__name__)


def dsp_alice(config: Configuration) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Execute Digital Signal Processing given the configuration.

    Args:
        config (Configuration): configuration object containing information for DSP.

    Returns:
        Tuple[np.ndarray, np.ndarray, np.ndarray]: sequence to send, quantum sequence (without pilots, Zadoff-Chu and padded zeros), symbols.
    """
    if config.alice is None:
        raise InvalidConfiguration(
            "The alice section is not present in the configuration file."
        )
    if config.frame is None:
        raise InvalidConfiguration(
            "The frame section is not present in the configuration file."
        )

    return dsp_alice_params(
        modulation_cls=config.frame.quantum.modulation_cls,
        variance=config.frame.quantum.variance,
        modulation_size=config.frame.quantum.modulation_size,
        num_symbols=config.frame.quantum.num_symbols,
        symbol_rate=config.frame.quantum.symbol_rate,
        roll_off=config.frame.quantum.roll_off,
        frequency_shift=config.frame.quantum.frequency_shift,
        pilots_amplitudes=config.frame.pilots.amplitudes,
        pilots_frequencies=config.frame.pilots.frequencies,
        zc_length=config.frame.zadoff_chu.length,
        zc_root=config.frame.zadoff_chu.root,
        zc_rate=config.frame.zadoff_chu.rate,
        num_zeros_start=config.frame.num_zeros_start,
        num_zeros_end=config.frame.num_zeros_end,
        dac_rate=config.alice.dac.rate,
        pulsed=config.frame.quantum.pulsed,
        load_final_sequence=config.alice.signal_generation.load_final_sequence,
        save_final_sequence=config.alice.signal_generation.save_final_sequence,
        final_sequence_path=config.alice.signal_generation.final_sequence_path,
        save_quantum_sequence=config.alice.signal_generation.save_quantum_sequence,
        quantum_sequence_path=config.alice.signal_generation.quantum_sequence_path,
        load_symbols=config.alice.signal_generation.load_symbols,
        save_symbols=config.alice.signal_generation.save_symbols,
        symbols_path=config.alice.signal_generation.symbols_path,
    )


# pylint: disable=too-many-arguments, too-many-locals, too-many-branches, too-many-statements
def dsp_alice_params(
    modulation_cls: Type[Modulation],
    variance: float,
    modulation_size: int,
    num_symbols: int,
    symbol_rate: float,
    roll_off: float,
    frequency_shift: float,
    pilots_amplitudes: np.ndarray,
    pilots_frequencies: np.ndarray,
    zc_length: int,
    zc_root: int,
    zc_rate: float,
    num_zeros_start: int,
    num_zeros_end: int,
    dac_rate: float,
    pulsed: bool = False,
    load_final_sequence: bool = False,
    save_final_sequence: bool = False,
    final_sequence_path: QOSSTPath = "",
    save_quantum_sequence: bool = False,
    quantum_sequence_path: QOSSTPath = "",
    load_symbols: bool = False,
    save_symbols: bool = False,
    symbols_path: QOSSTPath = "",
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Use the DSP of Alice to generate the sequence to the DAC using parameters.

    Args:
        modulation_cls (Type[Modulation]): modulation class to generate the symbols.
        variance (float): variance of the modulation to generate.
        modulation_size (int): modulation size in case of a finite modulation. Must be a power of 2. Must be a square for QAM. Set any value for Gaussian.
        num_symbols (int): number of symbols to generate.
        symbol_rate (float): symbol rate. Must be less than the dac rate.
        roll_off (float): roll off. Must be between 0 and 1.
        frequency_shift (float): frequency shift of the quantum symbols.
        pilots_amplitudes (np.ndarray): list of the amplitudes of the pilots.
        pilots_frequencies (np.ndarray): list of the frequencies of the pilots.
        zc_length (int): length of the Zadoff-Chu sequence. Must be coprime with the root.
        zc_root (int): root of the Zadoff-Chu sequence. Must be coprime with the length.
        zc_rate (float): rate of the Zadoff-Chu sequence. Must be less than the DAC rate. If 0 is given, the DAC rate is used.
        num_zeros_start (int): number of zeros to pad before the Zadoff-Chu sequence.
        num_zeros_end (int): number of zeros to pad after the end of the quantum sequence.
        dac_rate (float): dac rate.
        pulsed (bool, optional): if False, raised cosine filtering is used. If True, rectangular filtering is used. Defaults to False.
        load_final_sequence (bool, optional): load the final sequence instead of generating it if True. Defaults to False.
        save_final_sequence (bool, optional): save the final sequence if True. Defaults to False.
        final_sequence_path (QOSSTPath, optional): path to load or save the final sequence. Defaults to "".
        save_quantum_sequence (bool, optional): save the quantum sequence if True. Defaults to False.
        quantum_sequence_path (QOSSTPath, optional): path to save the quantum sequence. Defaults to "".
        load_symbols (bool, optional): load the symbols instead of generating them if True. Defaults to False.
        save_symbols (bool, optional): save the symbols if True. Defaults to False.
        symbols_path (QOSSTPath, optional): path to load or save the quantum symbols. Defaults to "".

    Returns:
        Tuple[np.ndarray, np.ndarray, np.ndarray]: sequence to send, quantum sequence (without pilots, Zadoff-Chu and padded zeros), symbols.
    """
    if load_final_sequence:
        logger.info(
            "Loading final sequence is on. Loading final sequence from %s, quantum sequence from %s and symbols from %s. Bypassing DSP.",
            final_sequence_path,
            quantum_sequence_path,
            symbols_path,
        )
        try:
            res = (
                np.load(final_sequence_path),
                np.load(quantum_sequence_path),
                np.load(symbols_path),
            )
        except FileNotFoundError:
            logger.critical("Loading files from config failed.")
            res = (None, None, None)
        return res

    # Get modulation and generate a baseband sequence

    sequence = generate_baseband_sequence(
        modulation_cls=modulation_cls,
        variance=variance,
        modulation_size=modulation_size,
        num_symbols=num_symbols,
        load_symbols=load_symbols,
        load_symbols_path=symbols_path,
        save_symbols=save_symbols,
        save_symbols_path=symbols_path,
    )
    symbols = np.copy(sequence)

    # Upsample sequence
    sps = int(dac_rate / symbol_rate)
    logger.info("Upsampling with factor %i.", sps)
    sequence = upsample(sequence, sps)

    # Apply filter
    if pulsed:
        logger.info("Using rectangular filter")
        sequence = apply_rectangular_filter(
            sequence,
            10 * sps + 2,
            roll_off,
            1 / symbol_rate,
            dac_rate,
        )
    else:
        logger.info("Using RRC filter")
        sequence = apply_rrc_filter(
            sequence,
            10 * sps + 2,
            roll_off,
            1 / symbol_rate,
            dac_rate,
        )

    # Shift sequence in frequency
    sequence = shift_sequence(sequence, frequency_shift, dac_rate)

    quantum_sequence = np.copy(sequence)

    if save_quantum_sequence:
        logger.info(
            "Saving quantum sequence at %s",
            quantum_sequence_path,
        )
        np.save(quantum_sequence_path, quantum_sequence)

    # Add frequency multipexed pilots
    sequence = add_frequency_multiplexed_pilots(
        sequence,
        pilots_frequencies,
        pilots_amplitudes,
        dac_rate,
    )

    # Normalize sequence

    # Add Zadoff-Chu sequence
    if zc_rate == 0:
        repeat = 1
    else:
        repeat = int(dac_rate / zc_rate)
    sequence = add_zc(
        sequence,
        zc_root,
        zc_length,
        repeat=repeat,
    )

    # Pad zeros
    sequence = add_zeros(sequence, num_zeros_start, num_zeros_end)

    if save_final_sequence:
        logger.info(
            "Saving final sequence at %s",
            final_sequence_path,
        )
        np.save(final_sequence_path, sequence)

    return sequence, quantum_sequence, symbols


# pylint: disable=too-many-arguments
def generate_baseband_sequence(
    modulation_cls: Type[Modulation],
    variance: float,
    modulation_size: int,
    num_symbols: int,
    load_symbols: bool = False,
    load_symbols_path: QOSSTPath = "",
    save_symbols: bool = False,
    save_symbols_path: QOSSTPath = "",
) -> np.ndarray:
    """
    Generate symbols for modulation, variance, modulation size and number of symbols.

    Args:
        modulation_cls (Type[Modulation]): modulation class.
        variance (float): variance.
        modulation_size (int): size of the modulation.
        num_symbols (int): number of symbols to generate.
        load_symbols (bool, optional): load the symbols instead of generating them if True. Defaults to False.
        load_symbols_path (QOSSTPath, optional): path to load the quantum symbols. Defaults to "".
        save_symbols (bool, optional): save the symbols if True. Defaults to False.
        save_symbols_path (QOSSTPath, optional): path to save the quantum symbols. Defaults to "".


    Returns:
        np.ndarray: array of the symbols.
    """
    if load_symbols:
        logger.info("Loading symbols from %s", load_symbols_path)
        return np.load(load_symbols_path)

    logger.info(
        "Generating symbol with modulation %s variance %f size %i",
        str(modulation_cls),
        variance,
        modulation_size,
    )
    modulation = modulation_cls(variance=variance, modulation_size=modulation_size)
    symbols: np.ndarray = modulation.modulate(size=num_symbols)

    if save_symbols:
        logger.info("Saving symbols to %s", save_symbols_path)
        np.save(save_symbols_path, symbols)
    return symbols


def upsample(sequence: np.ndarray, upsample_ratio: int) -> np.ndarray:
    """
    Upsample sequence by upsample_ratio.

    Args:
        sequence (np.ndarray): sequence to be upsampled.
        upsample_ratio (int): upsample ratio.

    Returns:
        np.ndarray: the upsampled sequence.
    """
    logger.info("Upsampling sequence with factor %i", upsample_ratio)
    upsampled_sequence = np.zeros(len(sequence) * upsample_ratio, dtype=complex)
    upsampled_sequence[int(upsample_ratio / 2) :: upsample_ratio] = sequence
    return upsampled_sequence


def apply_rrc_filter(
    sequence: np.ndarray,
    length: int,
    roll_off: float,
    symbol_period: float,
    sampling_rate: float,
) -> np.ndarray:
    """
    Filter sequence with a Root Raised Cosine filter.

    Args:
        sequence (np.ndarray): sequence to be filter.
        length (int): length of the RRC filter.
        roll_off (float): roll off of the RRC filter.
        symbol_period (float): sampling period, in seconds.
        sampling_rate (float): sampling rate in Hz.

    Returns:
        np.ndarray: filtered sequence.
    """
    logger.info("Applying RRC filter with length %i and roll_off %f", length, roll_off)
    _, filtre = root_raised_cosine_filter(
        length, roll_off, symbol_period, sampling_rate
    )
    filtre = filtre[1:]
    norm = np.sqrt(symbol_period * sampling_rate)
    return 1 / norm * signal.fftconvolve(sequence, filtre, "same")


def apply_rectangular_filter(
    sequence: np.ndarray,
    length: int,
    cyclic_ratio: float,
    symbol_period: float,
    sampling_rate: float,
) -> np.ndarray:
    """
    Filter sequence with rectangular filter.

    Args:
        sequence (np.ndarray): sequence to be filter.
        length (int): length of the rectangular filter.
        cyclic_ratio (float): cyclic ratio of the rectangular filter.
        symbol_period (float): sampling period, in seconds.
        sampling_rate (float): sampling rate in Hz.

    Returns:
        np.ndarray: filtered sequence
    """
    logger.info(
        "Applying rectangular filter with length %i and cyclir ratio %f",
        length,
        cyclic_ratio,
    )
    _, filtre = rect_filter(
        length,
        cyclic_ratio * symbol_period,
        sampling_rate,
    )
    filtre = filtre[1:]
    return signal.fftconvolve(sequence, filtre, "same")


def shift_sequence(
    sequence: np.ndarray, frequency_shift_value: float, sampling_rate: float
) -> np.ndarray:
    """
    Shift the sequence by frequency_shit_value.

    Args:
        sequence (np.ndarray): the sequence to be shifted.
        frequency_shift_value (float): the shift to apply in Hz.
        sampling_rate (float): the sampling rate in Hz.

    Returns:
        np.ndarray: shifted sequence.
    """
    logging.info("Shifting sequence with shift %f", frequency_shift_value * 1e-6)
    return sequence * np.exp(
        1j
        * 2
        * np.pi
        * np.arange(sequence.shape[0])
        * frequency_shift_value
        / sampling_rate
    )


def add_frequency_multiplexed_pilots(
    sequence: np.ndarray,
    pilots_frequencies: np.ndarray,
    pilots_amplitudes: np.ndarray,
    sampling_rate: float,
) -> np.ndarray:
    """
    Add pilots to the sequence, multiplexed in frequency.

    Args:
        sequence (np.ndarray): sequence to which add the pilots to.
        pilots_frequencies (np.ndarray): list of pilots frequencies, in Hz.
        pilots_amplitudes (np.ndarray): list of pilots amplitudes.
        sampling_rate (float): sampling rate, in Hz.

    Returns:
        np.ndarray: sequence with pilots added.
    """
    pilot_sequence = np.zeros(sequence.shape[0], dtype=complex)
    for i, frequency in enumerate(pilots_frequencies):
        logger.info(
            "Adding pilot with amplitude %f and frequency %f",
            pilots_amplitudes[i],
            frequency * 1e-6,
        )
        pilot_sequence += pilots_amplitudes[i] * np.exp(
            1j * 2 * np.pi * np.arange(sequence.shape[0]) * frequency / sampling_rate
        )
    return sequence + pilot_sequence


def add_zc(sequence: np.ndarray, root: int, length: int, repeat: int = 1) -> np.ndarray:
    """
    Add Zadoff-Chu sequence at the beginning of the sequence.

    Args:
        sequence (np.ndarray): sequence to which add the Zadoff-Chu sequence to.
        root (int): root of the Zadoff-Chu sequence.
        length (int): length of the Zadoff-Chu sequence.
        repeat (int, optional): repeat each element by this amount, useful to change the rate. Default to 1.

    Returns:
        np.ndarray: sequence with the Zadoff-Chu sequence added.
    """
    logger.info("Adding Zadoff-Chu with length %i and root %i", length, root)
    zadoff_chu = zcsequence(root, length)
    if repeat > 1:
        logger.info("Repeating Zadoff-Chu with repeat=%i", repeat)
        zadoff_chu = np.repeat(zadoff_chu, repeat)
    return np.concatenate((zadoff_chu, sequence))


def add_zeros(
    sequence: np.ndarray, num_zeros_start: int, num_zeros_end: int
) -> np.ndarray:
    """
    Add zeros at the beginning and end of the sequence.

    It adds num_zeros_start ad the beginning
    and num_zeros_end at then end.

    Args:
        sequence (np.ndarray): sequence to which add the zeros to.
        num_zeros_start (int): number of zeros in the beginning.
        num_zeros_end (int): number of zeros at the end.

    Returns:
        np.ndarray: sequence with padded zeros.
    """
    logger.info(
        "Adding %i zeros at the start and %i zeros at the end",
        num_zeros_start,
        num_zeros_end,
    )
    zeros_begin = np.zeros(num_zeros_start)
    zeros_end = np.zeros(num_zeros_end)
    return np.concatenate((zeros_begin, sequence, zeros_end))
