# Log Distance Propagation Loss Model


Please check below for a detailed implementation.
`wireless/SEED-Simulator/seedsim/propagationModel/PropagationLossModel.py
`

In essence, this model assumes that as the distance increases, the received signal power weakens. However, currently, we are adjusting the network's loss rate in the emulator, not the signal power. Therefore, when using this model, we set a minimum receivable signal power threshold (-82). When the signal power is greater than the threshold, we set the loss rate to 0. Conversely, when the signal power is less than the threshold, we set the loss rate to 100.

The Log Distance Propagation Loss Model, also known as the Log Distance Path Loss Model, is a mathematical model commonly used in wireless communications to characterize the attenuation or loss of signal strength as it propagates through a medium, typically the air. This model is particularly relevant in radio frequency (RF) and wireless communication systems.

The basic idea behind the Log Distance Propagation Loss Model is to express the relationship between the transmitted signal power and the received signal power as a logarithmic function of the distance between the transmitter and the receiver. The general form of the model is:

`PL(dB)=PL(d_0)+10⋅n⋅log_10(d/d_0)`
​

where:
- `PL(dB)` is the path loss in decibels (dB).
- `PL(d_0)` is the path loss at a reference distance d_0.
- `n` is the path loss exponent, indicating how quickly the signal strength decreases with distance.
- `d` is the distance between the transmitter and receiver.
