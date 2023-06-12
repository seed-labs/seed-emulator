#!/bin/env python3 
from simulation_util import *
import argparse

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest='command')

init = subparsers.add_parser('init', help='initialize nodes positisons')
move = subparsers.add_parser('move', help='move nodes positions')
move.add_argument("--counts","-c", dest="counts", action="store",
                    default=1,
                    help='move nodes for the given counts (default counts: 1)')

args = parser.parse_args()

if args.command == "init":
    sim = Simulation(override=True)
    sim.update_loss_on_containers()
elif args.command == "move":
    sim = Simulation()
    for i in range(int(args.counts)):
        sim.move_and_update_loss()
        sim.update_loss_on_containers()

