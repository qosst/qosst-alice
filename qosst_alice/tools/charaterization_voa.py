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
Tool for the calibration of a VOA, 
including attenuation relation, 
hysteresis, stability and modulation.
"""
import logging
import time
import datetime
import argparse
from dataclasses import dataclass, field

import numpy as np

from qosst_hal.voa import GenericVOA
from qosst_hal.adc import GenericADC
from qosst_hal.dacadc import GenericDACADC
from qosst_core.utils import get_object_by_import_path, configuration_menu
from qosst_core.data import BaseQOSSTData


DEFAULT_VOA = "qosst_hal.voa.FakeVOA"
DEFAULT_VOA_LOCATION = ""

DEFAULT_ADC = "qosst_hal.adc.FakeADC"
DEFAULT_ADC_LOCATION = ""

DEFAULT_DACADC = "qosst_hal.dacadc.FakeDACADC"

DEFAULT_VOLTAGE_START = 0
DEFAULT_VOLTAGE_END = 5.1
DEFAULT_VOLTAGE_STEP = 0.1

DEFAULT_VOLTAGE_LONG_ACQUISITION = 3
DEFAULT_TIME_LONG_ACQUISITION = 10
DEFAULT_RATE_LONG_ACQUISITION = 1e3

DEFAULT_RATE_ON_OFF = 1e3
DEFAULT_DURATION_ON_OFF = 5
DEFAULT_SAMPLES_ON_OFF = 10
DEFAULT_VALUE_ON_OFF = 3

logger = logging.getLogger(__name__)


class CharacterizationVOAData(BaseQOSSTData):
    """
    Data container for the output of the VOA characterization script.
    """

    max_power: float
    voltages_hysteresis: np.ndarray
    power_hysteresis: np.ndarray
    long_acquisition_data: np.ndarray
    input_on_off: np.ndarray
    on_off_data: np.ndarray
    date: datetime.datetime

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        max_power: float,
        voltages_hysteresis: np.ndarray,
        power_hysteresis: np.ndarray,
        long_acquisition_data: np.ndarray,
        input_on_off: np.ndarray,
        on_off_data: np.ndarray,
    ) -> None:
        """
        Args:
            max_power (float): maximal value registered at the photodiode (i.e. when the VOA is its lowest attenuation).
            voltages_hysteresis (np.ndarray): array for the test voltages for the hysteresis.
            power_hysteresis (np.ndarray): measured powers for each voltage of the hysteresis.
            long_acquisition_data (np.ndarray): measured powers for the long acquisition.
            input_on_off (np.ndarray): input voltages for the on-off modulation.
            on_off_data (np.ndarray): measured powers for the on-off modulation.
        """
        self.max_power = max_power
        self.voltages_hysteresis = voltages_hysteresis
        self.power_hysteresis = power_hysteresis
        self.long_acquisition_data = long_acquisition_data
        self.input_on_off = input_on_off
        self.on_off_data = on_off_data
        self.date = datetime.datetime.now()


# pylint: disable=too-many-instance-attributes
@dataclass
class Configuration:
    """
    Configuration class for the VOA calibration script.
    """

    voa: str = field(default=DEFAULT_VOA)
    voa_location: str = field(default=DEFAULT_VOA_LOCATION)
    adc: str = field(default=DEFAULT_ADC)
    adc_location: str = field(default=DEFAULT_ADC_LOCATION)
    dacadc: str = field(default=DEFAULT_DACADC)
    voltage_start: float = field(default=DEFAULT_VOLTAGE_START)
    voltage_end: float = field(default=DEFAULT_VOLTAGE_END)
    voltage_step: float = field(default=DEFAULT_VOLTAGE_STEP)
    voltage_long_acquisition: float = field(default=DEFAULT_VOLTAGE_LONG_ACQUISITION)
    time_long_acquisition: float = field(default=DEFAULT_TIME_LONG_ACQUISITION)
    rate_long_acquisition: float = field(default=DEFAULT_RATE_LONG_ACQUISITION)
    rate_on_off: float = field(default=DEFAULT_RATE_ON_OFF)
    duration_on_off: int = field(default=DEFAULT_DURATION_ON_OFF)
    samples_on_off: int = field(default=DEFAULT_SAMPLES_ON_OFF)
    value_on_off: float = field(default=DEFAULT_VALUE_ON_OFF)


# pylint: disable=too-many-locals, too-many-statements
def characterize_voa(args: argparse.Namespace):
    """
    Main function of the tool, that will be called by the execution script.
    It takes as a parameter the arguments of the command line as a namespace.

    Args:
        args (Namespace): arguments of the command line.
    """
    config = Configuration()

    print("#####################################################")
    print("## Welcome to the calibration of an electronic VOA ##")
    print("#####################################################")

    print(
        "This script will perform several tests on the VOA, including voltage response, hysteresis, modulation and stability.\n"
    )

    print("The VOA should be connected with the VOA interface, using a DAC.")
    print(
        "A photodiode connected to an ADC should be connected at the end of the VOA.\n"
    )

    print("A laser should be at the input of the VOA.\n")

    configuration_menu(config, preferred_config_name="config-characterization-voa")
    print(config)

    voa: GenericVOA = get_object_by_import_path(config.voa)(config.voa_location)
    photodiode: GenericADC = get_object_by_import_path(config.adc)(
        config.adc_location.split("@", maxsplit=1)[0],
        [config.adc_location.split("@")[1]],
    )

    voa.open()
    photodiode.open()
    photodiode.set_acquisition_parameters(acquisition_time=0.1)

    # Get reference by applying 0V and measuring the photodiode

    logger.info("Get value of photodiode at 0V.")

    voa.set_value(0)
    time.sleep(0.5)
    photodiode.arm_acquisition()
    photodiode.trigger()
    data = photodiode.get_data()[0]

    photodiode.stop_acquisition()

    max_power = np.mean(data)

    # First get characterization of the VOA and hysteresis
    # We do one way and return, twice

    logger.info("Hysteresis characterization")

    voltages = np.arange(config.voltage_start, config.voltage_end, config.voltage_step)

    voltages_hysteresis = np.concatenate(
        (voltages, voltages[::-1], voltages, voltages[::-1])
    )

    power_hysteresis = np.zeros(len(voltages_hysteresis))

    for i, voltage in enumerate(voltages_hysteresis):
        logger.info("Setting voltage %f V.", voltage)
        voa.set_value(voltage)
        time.sleep(0.5)
        photodiode.arm_acquisition()
        photodiode.trigger()
        data = photodiode.get_data()[0]

        photodiode.stop_acquisition()

        power_hysteresis[i] = np.mean(data)

    # Then let's do a long acquisition

    logger.info("Long acquisition")

    voa.set_value(config.voltage_long_acquisition)

    photodiode.close()

    photodiode_long: GenericADC = get_object_by_import_path(config.adc)(
        config.adc_location.split("@", maxsplit=1)[0],
        [config.adc_location.split("@")[1]],
    )

    photodiode_long.open()

    photodiode_long.set_acquisition_parameters(
        acquisition_time=config.time_long_acquisition,
        target_rate=config.rate_long_acquisition,
    )
    photodiode_long.arm_acquisition()
    photodiode_long.trigger()
    time.sleep(config.time_long_acquisition)

    long_acquisition_data = photodiode_long.get_data()[0]
    photodiode_long.stop_acquisition()

    voa.close()
    photodiode_long.close()

    # Finally let's check a on-off acquisition

    logger.info("Modulation")

    dacadc: GenericDACADC = get_object_by_import_path(config.dacadc)(
        config.voa_location, config.adc_location
    )
    dacadc.open()

    input_on_off = np.zeros(int(config.rate_on_off * config.duration_on_off))
    for i in range(config.samples_on_off):
        input_on_off[config.samples_on_off + i :: 2 * config.samples_on_off] = (
            config.value_on_off
        )

    dacadc.set_parameters(
        sample_rate=config.rate_on_off, number_of_samples=len(input_on_off)
    )
    dacadc.load_dac_data([input_on_off])

    dacadc.start()
    time.sleep(config.duration_on_off)
    on_off_data = dacadc.get_adc_data()[0]
    dacadc.stop()

    dacadc.close()

    # Save everything
    if args.save:
        to_save = CharacterizationVOAData(
            max_power=max_power,
            voltages_hysteresis=voltages_hysteresis,
            power_hysteresis=power_hysteresis,
            long_acquisition_data=long_acquisition_data,
            input_on_off=input_on_off,
            on_off_data=on_off_data,
        )
        filename = "voa-characterisation.qosst"
        to_save.save(filename)
        logger.info("Results were saved to %s", str(filename))
