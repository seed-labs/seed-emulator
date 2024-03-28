#!/bin/env python3 
from seedsim import *
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
    logDist = LogDistancePropagationLossModel()
    nakagami = NakagamiPropagationLossModel()
    constantDelay = ConstantSpeedPropagationDelayModel()
    sim.appendPropagationLossModel(lossModel=logDist)\
        .appendPropagationLossModel(lossModel=nakagami)
    sim.setPropagationDelayModel(delayModel=constantDelay)

    sim.move_nodes_by_manual([(0, 50, 50),
                    (1, 0, 50),
                    (2, 50, 0),
                    (3, 50, 100),
                    (4, 100, 50)])

    sim.update_loss_and_delay_on_containers()


elif args.command == "move":   
    sim = Simulation()
    logDist = LogDistancePropagationLossModel()
    nakagami = NakagamiPropagationLossModel()
    constantDelay = ConstantSpeedPropagationDelayModel()

    sim.appendPropagationLossModel(lossModel=logDist)\
        .appendPropagationLossModel(lossModel=nakagami)

    sim.setPropagationDelayModel(delayModel=constantDelay) 
    
    for i in range(int(args.counts)):
        sim.move_nodes()
        sim.update_loss_and_delay_on_containers()

