# Functionalities

`qosst-alice` provides the two main functionalities: the first one is the Digital Signal Processing for Alice and the second one is Alice's server.

## Digital Signal Processing

The Digital Signal Processing of Alice generates the symbol and makes the operations to prepare for the physical transmission, in particular by upsampling it, filtering it and adding classical information such as phase and clock reference, and synchronisation sequence.

The behaviour of the DSP is described extensively [here](../understanding/dsp.md).

## Server

`qosst-alice` provides a full server interface with the {external+qosst-core:doc}`QOSST control protocol <understanding/control_protocol>`, answering the requests of Bob. It uses the DSP function cited above to generate the sequence and apply it to the IQ modulator. It also includes the required functions for parameters estimation.

The behaviour of the server is described extensively [here](../understanding/server.md).