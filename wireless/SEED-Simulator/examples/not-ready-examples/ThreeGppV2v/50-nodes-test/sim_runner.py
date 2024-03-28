#!/bin/env python3 

from seedsim import *
import argparse
import time

parser = argparse.ArgumentParser()
parser.add_argument("--iter", "-i", dest="iter", action="store",
                    default=0,
                    help='update node to simulation info at given iterations (default counts: 0)')
args = parser.parse_args()


simRunner = SimRunner()
for i in range(50):
    simRunner.update_loss_and_delay_on_containers()
