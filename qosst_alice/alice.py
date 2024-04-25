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

# pylint: disable=too-many-lines

"""
Main script for QOSST Alice.

It contains Alice server class and the entrypoint of the server.
"""
import os
import logging
import argparse
import signal
import sys
import uuid
import time
import traceback
from pathlib import Path
from typing import Optional

import numpy as np

from qosst_hal.dac import GenericDAC
from qosst_hal.powermeter import GenericPowerMeter
from qosst_hal.laser import GenericLaser
from qosst_hal.voa import GenericVOA
from qosst_hal.modulator_bias_control import GenericModulatorBiasController

from qosst_core.utils import eph
from qosst_core.logging import create_loggers
from qosst_core.configuration import Configuration
from qosst_core.configuration.exceptions import InvalidConfiguration
from qosst_core.control_protocol import QOSST_VERSION
from qosst_core.control_protocol.sockets import QOSSTServer
from qosst_core.control_protocol.codes import QOSSTCodes, QOSSTErrorCodes
from qosst_core.infos import get_script_infos

from qosst_alice import __version__
from qosst_alice.dsp import dsp_alice

logger = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes,too-many-return-statements,too-many-boolean-expressions,too-many-branches,too-many-statements
class QOSSTAlice:
    """
    This server should be almost indestructible.
    """

    socket: QOSSTServer  #: The socket of the server

    # State variables
    client_connected: bool  #: True if a client is currently connected, False otherwise.
    client_initialized: bool  #: True if the client went through the identification process, False otherwise.
    frame_uuid: Optional[uuid.UUID]  #: The UUID of the current frame we are working on.
    frame_prepared: bool  #: True if the DSP has prepared the frame to send.
    frame_sent: bool  #: True if the frame was sent.
    frame_ended: bool  #: True if QIE has ended.
    pe_ended: bool  #: True if the parameter estimation step has ended.
    ec_initialized: bool  #: True if the error correction has started.
    ec_ended: bool  #: True if the error correction has ended.
    pa_ended: bool  #: True if the privacy amplification has ended.

    # Useful variables
    quantum_sequence: Optional[
        np.ndarray
    ]  #: An array with the quantum sequence, of the current frame.
    symbols: Optional[np.ndarray]  #: An array with the symbols, of the current frame.
    photon_number: float  #: The mean photon number of the current frame.

    # Hardware
    dac: GenericDAC  #: The DAC of Alice.
    powermeter: GenericPowerMeter  #: The powermeter of Alice.
    voa: GenericVOA  #: The VOA of Alice.
    bias_controller: (
        GenericModulatorBiasController  #: The bias controller for the modulator.
    )
    laser: GenericLaser  #: The laser of Alice.

    # Configuration
    config_path: str  #: The configuration path.
    config: Optional[Configuration]  #: The configuration object.

    def __init__(self, config_path: str):
        """
        Args:
            config_path (str): path of the configuration path.
        """
        print(get_script_infos())
        logger.info("Initialization QOSST Alice server")

        # State initialization
        self.client_connected = False
        self.client_initialized = False
        self.frame_uuid = None
        self.frame_prepared = False
        self.frame_sent = False
        self.frame_ended = False
        self.pe_ended = False
        self.ec_initialized = False
        self.ec_ended = False
        self.pa_ended = False

        # Useful variables initialization
        self.quantum_sequence = None
        self.symbols = None
        self.photon_number = 0

        # Configuration initialization
        self.config_path = config_path
        self.config = None

        self._load_config()

        self._init_hardware()

        self._init_socket()
        signal.signal(signal.SIGINT, self._interruption_handler)

    def _init_hardware(self) -> None:
        """
        Init the hardware (DAC, powermeter, VOA, laser, bias controller).
        """
        assert self.config is not None and self.config.alice is not None
        logger.info("Initializing hardware")
        logger.info("Opening DAC")
        self.dac = self.config.alice.dac.device()
        self.dac.open()
        self.dac.set_emission_parameters(
            channels=self.config.alice.dac.channels,
            dac_rate=self.config.alice.dac.rate,
            amplitude=self.config.alice.dac.amplitude,
            repeat=1,
            **self.config.alice.dac.extra_args,
        )
        logger.info(
            "Opening power at location %s", self.config.alice.powermeter.location
        )
        self.powermeter = self.config.alice.powermeter.device(
            self.config.alice.powermeter.location,
            timeout=self.config.alice.powermeter.timeout,
        )
        self.powermeter.open()

        logger.info(
            "Opening VOA (%s) at location %s",
            str(self.config.alice.voa.device),
            self.config.alice.voa.location,
        )
        self.voa = self.config.alice.voa.device(
            self.config.alice.voa.location, **self.config.alice.voa.extra_args
        )
        self.voa.open()
        logger.info("Applying value %f to the VOA", self.config.alice.voa.value)
        self.voa.set_value(self.config.alice.voa.value)

        logger.info(
            "Opening laser (%s) at location %s",
            str(self.config.alice.laser.device),
            self.config.alice.laser.location,
        )
        self.laser = self.config.alice.laser.device(self.config.alice.laser.location)
        self.laser.open()

        logger.info(
            "Setting parameters for the laser: %s",
            str(self.config.alice.laser.parameters),
        )
        self.laser.set_parameters(**self.config.alice.laser.parameters)
        logger.info("Enabling laser")
        self.laser.enable()
        logger.info("Laser enabled")

        logger.info(
            "Opening bias controller (%s) at location %s",
            str(self.config.alice.modulator_bias_control.device),
            self.config.alice.modulator_bias_control.location,
        )
        self.bias_controller = self.config.alice.modulator_bias_control.device(
            self.config.alice.modulator_bias_control.location
        )
        self.bias_controller.open()
        self.bias_controller.lock(**self.config.alice.modulator_bias_control.extra_args)

    def _load_config(self) -> None:
        """
        Load (or reload) the configuration file.
        """
        if self.config:
            logger.info("Reloading configuration at %s", self.config_path)
        else:
            logger.info("Loading configuration at %s", self.config_path)
        try:
            self.config = Configuration(self.config_path)
        except InvalidConfiguration as exc:
            logger.fatal(
                "The configuration cannot be read (%s). Priting the full traceback and closing the server.",
                str(exc),
            )
            print(traceback.format_exc())
            self.stop(error=True)

        assert self.config is not None

        if self.config.alice is None:
            raise InvalidConfiguration(
                "The alice section is absent from the configuration file."
            )
        if self.config.frame is None:
            raise InvalidConfiguration(
                "The frame section is absent from the configuration file."
            )
        if self.config.authentication is None:
            raise InvalidConfiguration(
                "The authentication section is absent from the configuration file."
            )

        # Check schema
        logger.info("Checking the emission schema")
        emission_schema = self.config.alice.schema
        logger.info("Schema is %s", str(emission_schema))
        emission_schema.check()
        logger.info("Detection emission accepted.")

    def _init_socket(self) -> None:
        """
        Initialize the QOSST server socket.
        """
        assert self.config is not None
        assert self.config.alice is not None
        assert self.config.authentication is not None
        logger.info("Initialization QOSST server socket")
        self.socket = QOSSTServer(
            self.config.alice.network.bind_address,
            self.config.alice.network.bind_port,
            self.config.authentication.authentication_class,
            self.config.authentication.authentication_params,
        )
        self.socket.open()

    def _reset(self) -> None:
        """
        Completly reset the state of the server.
        """
        logger.info("Resetting state of the server.")
        self.client_connected = False
        self.client_initialized = False
        self.frame_uuid = None
        self.frame_prepared = False
        self.frame_sent = False
        self.frame_ended = False
        self.pe_ended = False
        self.ec_initialized = False
        self.ec_ended = False
        self.pa_ended = False

        self.quantum_sequence = None
        self.symbols = None
        self.photon_number = 0

    def _interruption_handler(self, _signum, _frame) -> None:
        """The interruption handler of the script.

        When CTRL-C is pressed, 4 options are proposed:
        P: Print current config
        R: Reload the configuration file (after a change)
        T: Manually reset the state of the server.
        S: Stop the server.
        C: Cancel and start back from where we left.
        """
        logger.warning("CTRL-C pressed")
        print("You have pressed CTRL-C. Would you like to:\n")
        print("[P] Print the configuration")
        print(f"[R] Reload the configuration file ({self.config_path})")
        print("[T] Reset state of the server")
        print("[S] Stop the server")
        print("[C] Cancel your action\n")
        action = input("You input [P/R/T/S/C]: ")
        if action.lower() == "p":
            print(self.config)
        elif action.lower() == "r":
            self._load_config()
        elif action.lower() == "t":
            self._reset()
        elif action.lower() == "s":
            self.stop()

    def _wait_for_client(self) -> None:
        """
        Wait for a client to connect.
        """
        logger.info("Waiting for a client to connect.")
        self.socket.connect()
        self.client_connected = True

    def _check_code(self, code: QOSSTCodes) -> bool:
        """Check if code is expected depending on the state of the sever.

        Args:
            code (QOSSTCodes): the code of the received message.

        Returns:
            bool: True if the code is a vlaid command with respect to the current state of the server, False, otherwise.
        """
        if code == QOSSTCodes.IDENTIFICATION_REQUEST:
            return self.client_connected

        if code in (
            QOSSTCodes.INITIALIZATION_REQUEST,
            QOSSTCodes.INITIALIZATION_REQUEST_CONFIG,
        ):
            return self.client_connected and self.client_initialized

        if code == QOSSTCodes.QIE_REQUEST:
            return (
                self.client_connected
                and self.client_initialized
                and self.frame_uuid is not None
            )

        if code == QOSSTCodes.QIE_TRIGGER:
            return (
                self.client_connected
                and self.client_initialized
                and self.frame_uuid is not None
                and self.frame_prepared
            )

        if code == QOSSTCodes.QIE_ACQUISITION_ENDED:
            return (
                self.client_connected
                and self.client_initialized
                and self.frame_uuid is not None
                and self.frame_sent
            )

        if code in (
            QOSSTCodes.PE_SYMBOLS_REQUEST,
            QOSSTCodes.PE_NPHOTON_REQUEST,
            QOSSTCodes.PE_FINISHED,
        ):
            return (
                self.client_connected
                and self.client_initialized
                and self.frame_uuid is not None
                and self.frame_ended
            )

        if code == QOSSTCodes.EC_INITIALIZATION:
            return (
                self.client_connected
                and self.client_initialized
                and self.frame_uuid is not None
                and self.pe_ended
            )

        if code in (
            QOSSTCodes.EC_BLOCK,
            QOSSTCodes.EC_REMAINING,
            QOSSTCodes.EC_VERIFICATION,
        ):
            return (
                self.client_connected
                and self.client_initialized
                and self.frame_uuid is not None
                and self.ec_initialized
            )

        if code == QOSSTCodes.PA_REQUEST:
            return (
                self.client_connected
                and self.client_initialized
                and self.frame_uuid is not None
                and self.ec_ended
            )

        if code == QOSSTCodes.FRAME_ENDED:
            return self.pa_ended

        return False

    def get_state(self) -> str:
        """
        Return the current state of the server as an str.

        Returns:
            str: the current state of the server.
        """
        res = ""
        res += f"Client connected: {self.client_connected}"
        res += f"Client initialized: {self.client_initialized}"
        res += f"Frame UUID: {self.frame_uuid}"
        res += f"Frame prepared: {self.frame_prepared}"
        res += f"Frame sent: {self.frame_sent}"
        res += f"Frame ended: {self.frame_ended}"
        res += f"PE ended: {self.pe_ended}"
        res += f"EC initialized: {self.ec_initialized}"
        res += f"EC ended: {self.ec_ended}"
        res += f"PA ended: {self.pa_ended}"
        return res

    def serve(self):
        """
        Start the server.
        """
        while True:
            # If no client is connected, wait for a client to connect
            if not self.client_connected:
                logger.info("Client is not connected.")
                self._wait_for_client()
                continue

            # Wait to receive a message

            code, data = self.socket.recv()

            # Test if the code is an error
            if code in iter(QOSSTErrorCodes):
                logger.warning("QOSST Error Code received.")

                if code == QOSSTErrorCodes.SOCKET_DISCONNECTION:
                    logger.warning("Client has disconnected")
                    self.client_connected = False
                    continue

                if code == QOSSTErrorCodes.UNKOWN_CODE:
                    logger.warning("Unkown code received.")
                    self.socket.send(QOSSTCodes.UNKOWN_COMMAND)
                    continue

                if code == QOSSTErrorCodes.AUTHENTICATION_FAILURE:
                    logger.warning("Authentication failure")
                    logger.warning("Client is now considered not initialized")
                    self.client_initialized = False
                    self.socket.send(QOSSTCodes.AUTHENTICATION_INVALID)
                    continue

                if code == QOSSTErrorCodes.FRAME_ERROR:
                    logger.warning("Frame error")
                    self.socket.send(QOSSTCodes.INVALID_CONTENT)
                    continue

            # Now the received code is not an error code

            # Treat general codes (ABORT, INVALID_RESPONSE, DISCONNECTION)

            if code == QOSSTCodes.ABORT:
                logger.critical("Abort message has been received.")
                if data and "abort_message" in data:
                    logger.critical("Abort reason was: %s>", data["abort_message"])
                self.socket.send(QOSSTCodes.ABORT_ACK)
                self._reset()
                continue

            if code == QOSSTCodes.INVALID_RESPONSE:
                logger.error("Invalid response message has been received.")
                if data and "error_message" in data:
                    logger.error(
                        "Invalid response reason was: %s.", data["error_message"]
                    )
                self.socket.send(QOSSTCodes.INVALID_RESPONSE_ACK)
                continue

            if code == QOSSTCodes.DISCONNECTION:
                logger.info("Client is going to disconnect.")
                self.socket.send(QOSSTCodes.DISCONNECTION_ACK)
                self._reset()
                continue

            # Treat parameter changes
            if code == QOSSTCodes.CHANGE_PARAMETER_REQUEST:
                # This is a bit complicated
                # If we are asked to change a.b.c to x
                # we need to affect self.config.a.b.c to x
                # but we cannot directly access self.config.a.b.c
                # we need to recursively access until the one before the last
                # (it means, the last class) and then modify the attribute c of b
                # to x.
                # A special case if we directly want to change a value of self.config
                # in which case, we directly change.
                if not data or not "parameter" in data or not "value" in data:
                    logger.error("Parameter or value was missing from the content.")
                    self.socket.send(
                        QOSSTCodes.INVALID_CONTENT,
                        {
                            "error_message": "Parameter or value was missing from the content."
                        },
                    )
                full_attribute = data["parameter"]
                new_value = data["value"]

                logger.info(
                    "Client has requested to change parameter %s to new value: %s",
                    full_attribute,
                    str(new_value),
                )

                old_value = None
                changing_class = self.config
                changing_attribute = None
                if "." not in full_attribute:
                    changing_attribute = full_attribute
                else:
                    attribute_list = full_attribute.split(".")
                    changing_attribute = attribute_list[-1]
                    for attr in attribute_list[:-1]:
                        if hasattr(changing_class, attr):
                            changing_class = getattr(changing_class, attr)
                        else:
                            logger.warning(
                                "Parameter %s not found. Impossible to change it.",
                                full_attribute,
                            )
                            self.socket.send(
                                QOSSTCodes.PARAMETER_UNKOWN,
                                {"parameter": full_attribute},
                            )
                            continue

                logger.debug(
                    "Parameter to change in class %s", changing_class.__class__
                )

                # Now changing class should be set
                # and also changing_attribute
                # Check that attribute is in the class
                # Save old value
                # Put new value
                if not hasattr(changing_class, changing_attribute):
                    logger.warning(
                        "Parameter %s not found. Impossible to change it.",
                        full_attribute,
                    )
                    self.socket.send(
                        QOSSTCodes.PARAMETER_UNKOWN,
                        {"parameter": full_attribute},
                    )
                else:
                    old_value = getattr(changing_class, changing_attribute)
                    logger.info(
                        "Parameter %s found with old value %s. Setting new value %s.",
                        full_attribute,
                        str(old_value),
                        str(new_value),
                    )
                    setattr(changing_class, changing_attribute, new_value)
                    self.socket.send(
                        QOSSTCodes.PARAMETER_CHANGED,
                        {
                            "parameter": full_attribute,
                            "old_value": old_value,
                            "new_value": new_value,
                        },
                    )
                continue

            # Treat the case for polarisaton recovery

            if code == QOSSTCodes.REQUEST_POLARISATION_RECOVERY:
                self._start_polarisation_recovery()
                self.socket.send(QOSSTCodes.POLARISATION_RECOVERY_ACK)
                continue

            if code == QOSSTCodes.END_POLARISATION_RECOVERY:
                self._end_polarisation_recovery()
                self.socket.send(QOSSTCodes.POLARISATION_RECOVERY_ENDED)
                continue

            # Test if code is allowed at the current state of the server

            if not self._check_code(code):
                logger.warning(
                    "Code %s (%i) is not a valid command for the current state of the server. %s",
                    str(code),
                    int(code),
                    self.get_state(),
                )
                self.socket.send(QOSSTCodes.UNEXPECTED_COMMAND)
                continue

            # Identification request
            if code == QOSSTCodes.IDENTIFICATION_REQUEST:
                logger.info("Identification request received.")
                if (
                    not data
                    or not "serial_number" in data
                    or not "qosst_version" in data
                ):
                    logger.error(
                        "serial_number of qosst_version was not present in content."
                    )
                    self.socket.send(
                        QOSSTCodes.INVALID_CONTENT,
                        {
                            "code": int(code),
                            "error_message": "serial_number or qosst_version was not present in content.",
                        },
                    )
                    continue

                if data["qosst_version"] != QOSST_VERSION:
                    logger.error(
                        "QOSST versions are not compatible (server: %s, client: %s)",
                        QOSST_VERSION,
                        data["qosst_version"],
                    )
                    self.socket.send(
                        QOSSTCodes.INVALID_QOSST_VERSION,
                        {"qosst_version": QOSST_VERSION},
                    )
                    continue

                logger.info("Client (S/N %s) connected", data["serial_number"])
                self.client_connected = True
                self.client_initialized = True
                self.socket.send(
                    QOSSTCodes.IDENTIFICATION_RESPONSE,
                    {"serial_number": self.config.serial_number},
                )
                continue

            # Initialization request
            if code == QOSSTCodes.INITIALIZATION_REQUEST:
                logger.info("Initialization request received.")

                if not data or not "frame_uuid" in data:
                    logger.error("frame_uuid is missing from content.")
                    self.socket.send(
                        QOSSTCodes.INVALID_CONTENT,
                        {
                            "code": int(code),
                            "error_message": "frame_uuid was not present in content.",
                        },
                    )

                self.frame_uuid = uuid.UUID(data["frame_uuid"])
                # We should here check the parameters.
                # For now the server accept every initialization request.

                logger.info(
                    "Client initialized. Starting frame %s", str(self.frame_uuid)
                )

                self.socket.send(QOSSTCodes.INITIALIZATION_ACCEPTED)

                logger.info("Reinitializing frame parameters.")
                self.frame_prepared = False
                self.frame_sent = False
                self.frame_ended = False
                self.pe_ended = False
                self.ec_initialized = False
                self.ec_ended = False
                self.pa_ended = False
                self.quantum_sequence = None
                self.symbols = None
                self.photon_number = 0
                continue

            if code == QOSSTCodes.INITIALIZATION_REQUEST_CONFIG:
                logger.info("Configuration was requested by client.")

                # Not implemented yet
                logger.error("Request for config is not implemented yet.")
                self.socket.send(QOSSTCodes.UNEXPECTED_COMMAND)
                continue

            if code == QOSSTCodes.QIE_REQUEST:
                logger.info("QIE requested")

                dsp_success = self._do_dsp()

                if not dsp_success:
                    logger.critical("DSP unsuccessful. Sending ABORT message to client")
                    self.socket.send(
                        QOSSTCodes.ABORT, {"abort_message": "DSP was not successful"}
                    )
                    continue

                self.frame_prepared = True
                self.frame_sent = False
                self.frame_ended = False
                self.pe_ended = False
                self.ec_initialized = False
                self.ec_ended = False
                self.pa_ended = False

                self.socket.send(QOSSTCodes.QIE_READY)
                continue

            if code == QOSSTCodes.QIE_TRIGGER:
                logger.info("QIE trigger.")
                self._start_transmission()
                self.socket.send(QOSSTCodes.QIE_EMISSION_STARTED)
                self.frame_sent = True
                continue

            if code == QOSSTCodes.QIE_ACQUISITION_ENDED:
                logger.info("QIE acquisition ended.")
                self._stop_transmission()
                self.socket.send(QOSSTCodes.QIE_ENDED)
                self.frame_ended = True
                self.photon_number = self._estimate_photon_number()
                continue

            if code == QOSSTCodes.PE_SYMBOLS_REQUEST:
                if not data or not "indices" in data:
                    logger.error("Indices were not in the received data.")
                    self.socket.send(
                        QOSSTCodes.INVALID_CONTENT,
                        {
                            "code": int(code),
                            "error_message": {"indices were missing from content."},
                        },
                    )
                    continue

                indices = np.array(data["indices"])
                logger.debug("Indices: %s.", str(indices))

                logger.info("Sending symbols.")
                real = None
                imag = None
                try:
                    real = self.symbols[indices].real
                    imag = self.symbols[indices].imag
                except IndexError as exc:
                    logger.error("Requested indices raise IndexError: %s.", str(exc))
                    self.socket.send(
                        QOSSTCodes.PE_SYMBOLS_ERROR, {"error_message": str(exc)}
                    )
                    continue

                self.socket.send(
                    QOSSTCodes.PE_SYMBOLS_RESPONSE,
                    {
                        "symbols_real": real.tolist(),
                        "symbols_imag": imag.tolist(),
                    },
                )
                continue

            if code == QOSSTCodes.PE_NPHOTON_REQUEST:
                logger.info("Number of photon requested.")
                self.socket.send(
                    QOSSTCodes.PE_NPHOTON_RESPONSE, {"n_photon": self.photon_number}
                )
                continue

            if code == QOSSTCodes.PE_FINISHED:
                if (
                    not data
                    or not "n_photon" in data
                    or not "transmittance" in data
                    or not "excess_noise" in data
                    or not "electronic_noise" in data
                    or not "eta" in data
                    or not "key_rate" in data
                ):
                    logger.error(
                        "One of the following was missing from content: n_photon, transmittance, excess_noise, electronic_noise, eta, key_rate."
                    )
                    self.socket.send(
                        QOSSTCodes.INVALID_CONTENT,
                        {
                            "error_message": "One of the following was missing from content: n_photon, transmittance, excess_noise, electronic_noise, eta, key_rate."
                        },
                    )
                    continue

                if not data["key_rate"] > 0:
                    logger.error("Key rate is not positive (%f).", data["key_rate"])
                    self.socket.send(
                        QOSSTCodes.PE_DENIED, {"deny_message": "Key rate is null."}
                    )
                    continue

                logger.info("Parameters estimation is approved.")
                self.pe_ended = True
                self.socket.send(QOSSTCodes.PE_APPROVED)

            if code in (
                QOSSTCodes.EC_INITIALIZATION,
                QOSSTCodes.EC_BLOCK,
                QOSSTCodes.EC_REMAINING,
                QOSSTCodes.EC_VERIFICATION,
            ):
                logger.error("Error correction is not implemented yet.")

                self.socket.send(QOSSTCodes.UNEXPECTED_COMMAND)

            if code == QOSSTCodes.PA_REQUEST:
                logger.error("Privacy amplification is not implemented yet.")

                self.socket.send(QOSSTCodes.UNEXPECTED_COMMAND)

            if code == QOSSTCodes.FRAME_ENDED:
                logger.info("Frame %s ended.", str(self.frame_uuid))
                self.socket.send(
                    QOSSTCodes.FRAME_ENDED_ACK, {"frame_uuid": str(self.frame_uuid)}
                )
                logger.info("Resetting frame values")
                self.client_initialized = False
                self.frame_uuid = None
                self.frame_prepared = False
                self.frame_sent = False
                self.frame_ended = False
                self.pe_ended = False
                self.ec_initialized = False
                self.ec_ended = False
                self.pa_ended = False

                self.quantum_sequence = None
                self.symbols = None
                self.photon_number = 0

    def _do_dsp(self) -> bool:
        """
        Apply the DSP using the configuration and load the sequence in the DAC.

        Returns:
            bool: True if the DSP and loading were successful, False otherwise.
        """
        assert self.config is not None and self.config.alice is not None
        logger.info("Starting DSP")
        final, self.quantum_sequence, self.symbols = dsp_alice(self.config)

        # Verify that sequence is between -1 and +1
        if (
            np.max(final.real) > 1
            or np.max(final.imag) > 1
            or np.min(final.real) < -1
            or np.min(final.imag) < -1
        ):
            logger.critical(
                "Final sequence is not fit to be sent (i.e. is not between -1 and 1). Aborting"
            )
            return False

        if self.config.alice.artificial_excess_noise:
            logger.warning(
                "Loading data with additional excess noise of %f",
                self.config.alice.artificial_excess_noise,
            )
            self.dac.load_data(
                [
                    final.real
                    + np.random.normal(
                        loc=0,
                        scale=np.sqrt(self.config.alice.artificial_excess_noise / 2),
                        size=len(final),
                    ),
                    final.imag
                    + np.random.normal(
                        loc=0,
                        scale=np.sqrt(self.config.alice.artificial_excess_noise / 2),
                        size=len(final),
                    ),
                ]
            )
        else:
            logger.info("Loading data into DAC.")
            self.dac.load_data([final.real, final.imag])
        logger.info("DSP ended")
        return True

    def _start_transmission(self) -> None:
        """
        Start the transmission.
        """
        logger.info("Starting emission")
        self.dac.start_emission()

    def _stop_transmission(self) -> None:
        """
        Stop the transmission.
        """
        self.dac.stop_emission()
        logger.info("Emission stopped")

    def _estimate_photon_number(self) -> float:
        """Estimate the photon number by reemitting the
        quantum data and reading the photodiode.

        Returns:
            float: the mean photon number at Alice's output.
        """
        assert self.config is not None
        assert self.config.alice is not None
        assert self.config.frame is not None
        assert self.quantum_sequence is not None
        self.dac.set_emission_parameters(
            channels=self.config.alice.dac.channels,
            dac_rate=self.config.alice.dac.rate,
            amplitude=self.config.alice.dac.amplitude,
            repeat=0,
            **self.config.alice.dac.extra_args,
        )

        number_repetitions = 20
        power_no_light = 0.0
        for _ in range(number_repetitions):
            power_no_light += self.powermeter.read()
            time.sleep(0.1)

        power_no_light = power_no_light / number_repetitions

        self.dac.load_data([self.quantum_sequence.real, self.quantum_sequence.imag])
        self.dac.start_emission()

        time.sleep(0.5)

        power_light = 0.0
        for _ in range(number_repetitions):
            power_light += self.powermeter.read()
            time.sleep(0.1)

        power_light = power_light / number_repetitions

        self.dac.stop_emission()
        self.dac.set_emission_parameters(
            channels=self.config.alice.dac.channels,
            dac_rate=self.config.alice.dac.rate,
            amplitude=self.config.alice.dac.amplitude,
            repeat=1,
            **self.config.alice.dac.extra_args,
        )

        mean_photon_number = (power_light - power_no_light) / (
            self.config.frame.quantum.symbol_rate
            * eph(self.config.alice.emission_wavelength)
        )
        mean_photon_final = (
            mean_photon_number * self.config.alice.photodiode_to_output_conversion
        )
        logger.info("Photon number was estimated at <n>=%f", mean_photon_final)
        return mean_photon_final

    def _start_polarisation_recovery(self):
        """
        Start the polarisation recovery by sending a classical signal (sine).
        """
        assert self.config is not None
        assert self.config.alice is not None

        logger.info("Starting emission for polarisation recovery")

        self.dac.set_emission_parameters(
            channels=self.config.alice.dac.channels,
            dac_rate=self.config.alice.dac.rate,
            amplitude=self.config.alice.dac.amplitude,
            repeat=0,
            **self.config.alice.dac.extra_args,
        )
        times = np.arange(100000)
        data = self.config.alice.polarisation_recovery.signal_amplitude * np.exp(
            1j
            * 2
            * np.pi
            * self.config.alice.polarisation_recovery.signal_frequency
            * times
            / self.config.alice.dac.rate
        )
        self.dac.load_data([data.real, data.imag])
        self.dac.start_emission()

    def _end_polarisation_recovery(self):
        """
        End the polarisation recovery by stopping the classical signal (sine).
        """
        logger.info("Stopping emission for polarisation recovery.")
        self.dac.stop_emission()
        self.dac.set_emission_parameters(
            channels=self.config.alice.dac.channels,
            dac_rate=self.config.alice.dac.rate,
            amplitude=self.config.alice.dac.amplitude,
            repeat=1,
            **self.config.alice.dac.extra_args,
        )

    def start(self):
        """
        Start the server.
        """
        self.serve()

    def stop(self, error=False):
        """
        Gracefuly stop the server.
        """
        logger.warning("Stopping the server")
        logger.info("Closing hardware")
        self.laser.disable()
        self.laser.close()
        self.dac.close()
        self.powermeter.close()
        self.voa.close()
        self.bias_controller.close()
        logger.info("Closing socket")
        self.socket.close()
        if error:
            sys.exit(1)
        sys.exit(0)


def _create_main_parser() -> argparse.ArgumentParser:
    """
    Create the parser for the command line tool.

    Returns:
        argparse.ArgumentParser: the created parser.
    """
    default_config_location = Path(os.path.abspath(__file__)).parent / "config.toml"

    parser = argparse.ArgumentParser(prog="qosst-alice")

    parser.add_argument("--version", action="version", version=__version__)

    parser.add_argument(
        "-f",
        "--file",
        default=default_config_location,
        help="Path of the configuration file. Default: config.toml in current folder.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Level of verbosity. If none, nothing is printed to the console. -v will print warnings and errors, -vv will add info and -vvv will print all debug logs.",
    )
    return parser


def main():
    """
    Create the parser, parse the arguments, start the logs and start alice's server.
    """
    parser = _create_main_parser()

    args = parser.parse_args()

    # Set loggers
    create_loggers(args.verbose, args.file)

    alice = QOSSTAlice(args.file)
    alice.start()


if __name__ == "__main__":
    main()
