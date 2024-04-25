# Server

The script of Alice is playing the role of a **server**, responding to Bob requests. In this section we go deeper in the server structure of Alice.

```{warning}

Alice only supports **one** client. Any attempt of connecting several clients will currently not work.
```

## What it means to be server

For Alice to be a server, it means that in general, after the initialisation, every action follows a request by Bob and that every message answers a message request from Bob.

In practice, Alice waits for a message. When she receives a message, Alice looks at her internal state, and the code (*i.e.* meaning) of the message and depending on this two input decides what to do (either do what Bob is asking or not).

The internal state is defined with variables that are update to know where in the protocol we are. Alice has a function to reset its internal state ({py:meth}`qosst_alice.alice.QOSSTAlice._reset`) in case of disconnection of the client or abortion of the frame.

## Internal state

The internal state is defined by the following attributes of {py:class}`QOSSTAlice <qosst_alice.alice.QOSSTAlice>`:

* {py:attr}`qosst_alice.alice.QOSSTAlice.client_connected`
* {py:attr}`qosst_alice.alice.QOSSTAlice.client_initialized`
* {py:attr}`qosst_alice.alice.QOSSTAlice.frame_uuid`
* {py:attr}`qosst_alice.alice.QOSSTAlice.frame_prepared`
* {py:attr}`qosst_alice.alice.QOSSTAlice.frame_sent`
* {py:attr}`qosst_alice.alice.QOSSTAlice.frame_ended`
* {py:attr}`qosst_alice.alice.QOSSTAlice.pe_ended`
* {py:attr}`qosst_alice.alice.QOSSTAlice.ec_initialized`
* {py:attr}`qosst_alice.alice.QOSSTAlice.ec_ended`
* {py:attr}`qosst_alice.alice.QOSSTAlice.pa_ended`

The current state of the server can be retrieved as a string by using the {py:meth}`qosst_alice.alice.QOSSTAlice.get_state` method.

The state is used to determine if an incoming code (*i.e* meaning) of the message makes sense in the current context, and this logic is done in the {py:meth}`qosst_alice.alice.QOSSTAlice._check_code` method. If the received code makes sense with the current state, `True` is returned meaning that the server should proceed the request. If `False` is returned, this means the request shouldn't be proceeded, and Alice will typically answer with the `QOSSTCodes.UNEXPECTED_COMMAND` message.

Some special requests are not tested with the {py:meth}`_check_code() <qosst_alice.alice.QOSSTAlice._check_code>` method (abort or disconnection for instance).

Alice can reset its internal state by using the {py:meth}`_reset() <qosst_alice.alice.QOSSTAlice._reset>` method.
## Reception of a message

Upon reception of a message, containing a code and a content, Alice will perform the following operations, in order:

1. Test if the code is special error code (`SOCKET_DISCONNECTION`, `UNKOWN_CODE`, `AUTHENTICATION_FAILURE` or `FRAME_ERROR`).  If the code was not a special error code, Alice proceeds to the next step. 
   * If the first happens, it means that the client has disconnected, and Alice will reset its state and wait for a new client.
   * If the second happens, it means that the code doesn't make sense for the QOSST control protocol and Alice answers with `UNKNOWN_COMMAND`.
   * If the third happens, it means that a step as went wrong in the authentication procedure, and Alice will send the `AUTHENTICATION_INVALID` code and consider the client as being not initialized anymore.
   * If the last happens, it means that the frame was not well formatted in accordance with the QOSST control protocol and Alice sends the `INVALID_CONTENT` message.
2. The general codes are treated first. This include `ABORT`, `INVALID_RESPONSE`, `DISCONNECTION` and `CHANGE_PARAMETER_REQUEST`. If the code is not one of them, Alice proceeds to the next step.
   * The first one is Bob aborting the exchange, in which case, Alice sends an `ABORT_ACK` and reset its internal state.
   * The second one is Bob indicating that the last answer from Alice didn't make sense, in which case the invalid reason is logged, and Alice sends the `INVALID_RESPONSE_ACK`.
   * The third one is Bob indicating its disconnection to Alice, in which case Alice sends the `DISCONNECTION_ACK` and reset its internal state. 
   * Finally the last one is Bob requesting a change of parameter in the configuration. Depending on Alice policy, it will perform or not the change and answer accordingly.
3. Alice tests if the received code makes sense with the current state of the server with the {py:meth}`_check_code() <qosst_alice.alice.QOSSTAlice._check_code>` method. If it doesn't make sense, Alice sends the `UNEXPECTED_COMMAND` code.
4. Then Alice will react depending on which code was received, and the behaviour is described below:
   * `IDENTIFICATION_REQUEST`: check serial number and QOSST version and initialize the authentication.
   * `INITIALIZATION_REQUEST`: save the new frame UUID sent by Bob and check parameters and reset some parameters to start a new frame.
   * `INITIALIZATION_REQUEST_CONFIG`: should send a configuration proposition. **Not implemented yet**.
   * `QIE_REQUEST`: run the DSP to generate the sequence. Answer with `QIE_READY`.
   * `QIE_TRIGGER`: trigger the acquisition. Answer with `QIE_EMISSION_STARTED`.
   * `QIE_ACQUISITION_ENDED`: stop the DAC. Answer with `QIE_ENDED`. Estimate the mean number of photons.
   * `PE_SYMBOLS_REQUEST`: get the indices from the request and send back the symbols at those indices using the `PE_SYMBOLS_RESPONSE` code.
   * `PE_NPHOTON_REQUEST`: send the average number of photons per symbols {math}`\langle n \rangle` to Bob using the `PE_NPHOTON_RESPONSE`.
   * `PE_FINISHED`: extract the average number of photons per symbols, the transmittance, the excess noise, the electronic noise, the detector efficiency an the key rate that was computed by Bob and accept if the key rate is strictly more than 0 with `PE_APPROVED` or deny with `PE_DENIED` if the key rate is 0.
   * `EC_INITIALIZATION`, `EC_BLOCK`, `EC_REMAINING`, `EC_VERIFICATION`: answer with `UNEXPECTED_COMMAND` as the error correction is not implemented yet.
   * `PA_REQUEST`: answer with `UNEXPECTED_COMMAND` as the privacy amplification is not implemented yet.
   * `FRAME_ENDED`: answer with `FRAME_ENDED_ACK` and reset frame values.

## Estimation of the number of photon

One of the main tasks of Alice, apart from generating the signal sequence, applying to the hardware and answering to Bob requests, is to measure the average number of photons per symbol at Alice's output {math}`\langle n \rangle`. This value is crucial as it will be used to measure the transmittance and in the computation of the secret key rate at Alice's modulation strength {math}`V_A` is {math}`V_A=2\langle n \rangle`.

In theory, this is easy to estimate: take the optical power {math}`P` and divide it by the rate of the symbols {math}`R_S` and the energy of a single photon at the considered wavelength {math}`E_{ph} = \frac{hc}{\lambda}`.

However this is not that simple, for several reasons:

* first, the optical power is usually measured using a monitoring photodiode, but their is some attenuation between this monitoring photodiode and the actual output of Alice. This is usually taken into account by adding a {math}`r_{conv}` factor such that {math}`P_{out} = r_{conv}\cdot P_{monitoring}` and this factor has to be calibrated.
* then, the optical power should only correspond to the quantum symbols, and should not have contribution from the finite extinction ratio of the modulator, or from the other classical data we are adding into the sequence;
* finally, the last issue is acquiring this data in real time, *i.e* at the same time as the data is sent to Bob.

Due to some limitations in our hardware, in particular the fact that it's not possible to read from the powermeter in real time, we choose a technique that is not real time.

Indeed the procedure is the following: when the sequence is generated, we also save the *quantum sequence* that is only composed of the quantum symbols and does not contain the pilots. Then after the whole sequence has been sent to Bob, we measure the power without sequence {math}`P_{monitoring,0}` and the power with a continuous emission of the quantum sequence {math}`P_{monitoring}`. Finally the average number of photons per symbol is given as 

```{math}
\langle n \rangle = r_{conv}\cdot \frac{P_{monitoring} - P_{monitoring, 0}}{E_{ph}\cdot R_S}
```

The subtraction of {math}`P_{monitoring,0}` allows to not take into account the part coming from the finite extinction ratio.

## Interruption handler

When using the server, it is usually possible to use the "CTRL+C" shortcut to get into an interactive menu.

```{warning}
We strongly suggest to use this feature when the server is in an IDLE state.
```

The interruption will read like this:

```{code-block} text

2023-07-17 14:09:59,968 - qosst_core.control_protocol.sockets - INFO - Waiting for a client to connect
^C2023-07-17 14:10:01,140 - qosst_alice.alice - WARNING - CTRL-C pressed
You have pressed CTRL-C. Would you like to:

[P] Print the configuration
[R] Reload the configuration file (config.toml)
[T] Reset state of the server
[S] Stop the server
[C] Cancel your action

You input [P/R/T/S/C]:
```

Five actions are proposed, that can be chosen by typing the character (lowercase or uppercase) and pressing "Enter". Leaving this blank and pressing "Enter" will have the same behaviour as "Cancel your action"

* `P` will print the configuration and resume the normal behaviour of the server;
* `R` will perform a reload in the configuration. This can be useful to change a parameter without relaunching the server;
* `T` will reset the status of the server (*i.e* the different status variables);
* `S` will gracefully stop the server;
* `C` will cancel the interruption and resume the normal behaviour of the server.

```{warning}

Note however that if you reload the configuration, any modification on the hardware will have no effect since the hardware will be already loaded.
```