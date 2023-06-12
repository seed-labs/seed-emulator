#!/usr/bin/env python3
# encoding: utf-8

import time
from simulation_util import *

sim = Simulation()

sim.move_nodes([(0, 0, 0),
                (1, 250, 0),
                (2, 250, 250),
                (3, 500, 0),
                (4, 500, 500)])

sim.update_loss_on_containers()
