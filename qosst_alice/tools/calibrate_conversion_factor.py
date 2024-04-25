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
Functions and script to calibrate the conversion factor of Alice.
"""
import time
import logging
import argparse
import datetime
from dataclasses import dataclass, field, fields

import numpy as np
from qosst_core.utils import get_object_by_import_path, configuration_menu
from qosst_core.data import BaseQOSSTData

logger = logging.getLogger(__name__)

DEFAULT_POWERMETER_1_CLASS: str = (
    "qosst_hal.powermeter.FakePowerMeter"  #: Default value for the first powermeter class.
)
DEFAULT_POWERMETER_2_CLASS: str = (
    "qosst_hal.powermeter.FakePowerMeter"  #: Default value for the second powermeter class.
)
DEFAULT_POWEMETER_1_LOCATION: str = (
    ""  #: Default value for the first powermeter location.
)
DEFAULT_POWEMETER_2_LOCATION: str = (
    ""  #: Default value for the second powermeter class.
)
DEFAULT_VOA_1_CLASS: str = (
    "qosst_hal.voa.FakeVOA"  #: Default value for the first VOA class.
)
DEFAULT_VOA_2_CLASS: str = (
    "qosst_hal.voa.FakeVOA"  #: Default value for the second VOA class.
)
DEFAULT_VOA_1_LOCATION: str = ""  #: Default value for the first VOA device.
DEFAULT_VOA_2_LOCATION: str = ""  #: Default value for the second VOA device.
DEFAULT_VOA_START_VALUE: float = 1.0  #: Default start value for the VOA.
DEFAULT_VOA_END_VALUE: float = 5.0  #: Default end value for the VOA.
DEFAULT_VOA_STEP_VALUE: float = 0.05  #: Default step value for the VOA.


class CalibrateConversionFactorData(BaseQOSSTData):
    """
    Data container for he output of the calibration script of the conversion factor.
    """

    pm1: np.ndarray
    pm2: np.ndarray
    conversion_factor: float
    date: datetime.datetime

    def __init__(
        self, pm1: np.ndarray, pm2: np.ndarray, conversion_factor: float
    ) -> None:
        """
        Args:
            pm1 (np.ndarray): array of powers on the first powermeter.
            pm2 (np.ndarray): array of powrs on the second powermeter.
            conversion_factor (float): value of the conversion factor between the two powermeters.
        """
        self.pm1 = pm1
        self.pm2 = pm2
        self.conversion_factor = conversion_factor
        self.date = datetime.datetime.now()


@dataclass
class Configuration:
    """
    Configuration object for the calibration of the conversion factor.
    """

    # pylint: disable=too-many-instance-attributes

    powermeter_1_class: str = field(
        default=DEFAULT_POWERMETER_1_CLASS
    )  #: The class for the first powermeter.
    powermeter_2_class: str = field(
        default=DEFAULT_POWERMETER_2_CLASS
    )  #: The class for the first powermeter.
    powermeter_1_location: str = field(
        default=DEFAULT_POWEMETER_1_LOCATION
    )  #: The location of the first power meter.
    powermeter_2_location: str = field(
        default=DEFAULT_POWEMETER_2_LOCATION
    )  #: The location for the second power meter.
    voa_1_class: str = field(
        default=DEFAULT_VOA_1_CLASS
    )  #: The class for the first VOA.
    voa_2_class: str = field(
        default=DEFAULT_VOA_2_CLASS
    )  #: The class for the second VOA.
    voa_1_location: str = field(
        default=DEFAULT_VOA_1_LOCATION
    )  #: The device of the first VOA.
    voa_2_location: str = field(
        default=DEFAULT_VOA_2_LOCATION
    )  #: The device of the second VOA.
    voa_start_value: float = field(
        default=DEFAULT_VOA_START_VALUE
    )  #: The start value of the VOA.
    voa_end_value: float = field(
        default=DEFAULT_VOA_END_VALUE
    )  #: The end value of the VOA.
    voa_step_value: float = field(
        default=DEFAULT_VOA_STEP_VALUE
    )  #: The step value of the VOA.

    def __str__(self) -> str:
        res = ""
        for class_field in fields(self.__class__):
            res += f"{class_field.name}: {getattr(self, class_field.name)}\n"
        return res


# pylint: disable=too-many-locals, too-many-instance-attributes
def calibration_conversion_factor(args: argparse.Namespace) -> None:
    """
    Estimate the conversion factor by taking the power at the output of Alice
    and the power usually measured by Alice.

    Args:
        args (argparse.Namespace): the arguments, in particular the save.
    """
    config = Configuration()

    print("##################################################################")
    print("## Welcome to the calibration of the conversion factor of Alice ##")
    print("##################################################################")

    print("The first VOA should be the one that Alice will use in normal operation.")
    print("The second VOA should be the channel VOA.\n")

    print(
        "The first powermeter should be the one that Alice will use in normal operation."
    )
    print("The second powermeter should be placed at Alice's output.\n")

    print(
        "A laser should be at the input of the first VOA with power such that both powermeters are not satured if the VOA are polarized.\n"
    )

    configuration_menu(config, preferred_config_name="config-conversion-factor")
    print(config)

    voa_values = np.arange(
        config.voa_start_value, config.voa_end_value, config.voa_step_value
    )

    powers_pm_1 = np.zeros(len(voa_values))
    powers_pm_2 = np.zeros(len(voa_values))
    voa_1_class = get_object_by_import_path(config.voa_1_class)
    voa_2_class = get_object_by_import_path(config.voa_2_class)
    powermeter_1_class = get_object_by_import_path(config.powermeter_1_class)
    powermeter_2_class = get_object_by_import_path(config.powermeter_2_class)

    voa1 = voa_1_class(config.voa_1_location, task_name="VOA1 task")
    voa2 = voa_2_class(config.voa_2_location, task_name="VOA2 task")
    pm1 = powermeter_1_class(config.powermeter_1_location, timeout=100)
    pm2 = powermeter_2_class(config.powermeter_2_location, timeout=100)

    voa1.open()
    voa2.open()
    voa2.set_value(0)  # Set the channel to no attenuation
    pm1.open()
    pm2.open()

    for i, voa_value in enumerate(voa_values):
        logger.info("Starting %i/%i", i + 1, len(voa_values))

        logger.info("Setting voa to %f", voa_value)
        voa1.set_value(voa_value)
        time.sleep(0.5)
        powers_pm_1[i] = pm1.read()
        powers_pm_2[i] = pm2.read()
        time.sleep(0.5)

    pm1.close()
    pm2.close()
    voa1.close()
    voa2.close()

    conversion_factor, _ = np.polyfit(powers_pm_1, powers_pm_2, 1)

    logger.info("The conversion factor was estimated at %.20f", conversion_factor)

    # Save the results if the --no-save parameter was not passed
    if args.save:
        filename = "calibration-conversion-factor.qosst"
        to_save = CalibrateConversionFactorData(
            pm1=powers_pm_1, pm2=powers_pm_2, conversion_factor=conversion_factor
        )
        to_save.save(filename)
        logger.info("Data was saved at %s.", filename)
