# Three Gpp V2v Urban Propagation Model

3GPP (3rd Generation Partnership Project) V2V (Vehicle-to-Vehicle) Urban Propagation Loss Model is a model used to estimate the radio signal propagation loss in urban environments for V2V communication systems. This model is designed to characterize how the strength of a radio signal diminishes as it travels between vehicles in urban settings.

The propagation loss models in 3GPP V2V systems take into account various factors such as buildings, vehicles, and other obstacles that can affect signal propagation in urban environments. The urban model is specifically tailored to address the challenges posed by the presence of buildings and other structures in densely populated areas.

The details of the 3GPP V2V Urban Propagation Loss Model may involve considerations like path loss, shadowing, and other parameters that influence the communication range and reliability between vehicles.

We referred to the NS3 Propagation Loss Model here(https://www.nsnam.org/docs/models/html/propagation.html#threegpppropagationlossmodel
) while writing our code. NS3 adopts a method for calculating received signal power, but we require loss rates instead of signal power. This is because, in the emulator, we change the network communication state using the tc command by modifying the loss rate. Therefore, to meet these requirements, our SEED simulator introduces a method to calculate loss rates instead of signal power. You can find the detailed code implementation here(wireless/SEED-Simulator/seedsim/propagationModel/ThreeGppPropagationLossModel.py
).

At the current stage, shadowing is not being considered, and it is one of the tasks that we need to develop in the future.