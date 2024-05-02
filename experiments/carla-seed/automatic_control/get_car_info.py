#!/usr/bin/env python3
import argparse  # Used for handling command line arguments
import carla  # Python API for CARLA simulator
import asyncio  # Asynchronous I/O, event loop, coroutines and tasks
import websockets  # Websockets library for client and server
import json  # JSON encoder and decoder
import math  # Mathematical functions

# Setup command-line argument parsing
parser = argparse.ArgumentParser(description="Get your car information")
parser.add_argument("--c_ip", default="localhost", help="IP address of the CARLA server")
parser.add_argument("--c_port", default=2000, type=int, help="Port number of the CARLA server")
parser.add_argument("--info", help="Get detailed info for a car based on its role name")

# Parse arguments from the command line
args = parser.parse_args()

async def get_vehicle_info(role_name):
    # Connect to the CARLA server
    client = carla.Client(args.c_ip, args.c_port)
    client.set_timeout(10.0)  # Set timeout for network operations
    world = client.get_world()  # Retrieve the world that is currently running on the server

    try:
        while True:  # Continuous loop to keep checking for vehicle info
            vehicle_actors = world.get_actors().filter('vehicle.*')  # Get all vehicles in the simulation
            found = False  # Flag to check if the vehicle is found
            for vehicle in vehicle_actors:
                # Check if the vehicle's role name matches the specified role name
                if vehicle.attributes.get('role_name', '') == role_name:
                    # Retrieve and format vehicle's location
                    location = vehicle.get_location()
                    location_str = f"({location.x:.2f}, {location.y:.2f}, {location.z:.2f})"
                    
                    # Calculate vehicle's speed in km/h from its velocity
                    velocity = vehicle.get_velocity()
                    speed_kmh = 3.6 * math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)
                    controls = vehicle.get_control()  # Retrieve vehicle's control inputs
                    
                    # Retrieve the vehicle type (model)
                    car_type = vehicle.type_id

                    # Output the vehicle information
                    print(f"Vehicle ID: {vehicle.id} with role: {role_name}")
                    print(f"Location: {location_str}")
                    print(f"Speed: {speed_kmh:.2f} km/h")
                    print(f"Car Type: {car_type}")
                    print(f"Throttle: {controls.throttle:.2f},\nBrake: {controls.brake:.2f},\nSteer: {controls.steer:.2f},\nReverse: {controls.reverse},\nHand Brake: {controls.hand_brake}\n")
                    found = True

                    break  # Exit loop after finding the vehicle
            if not found:
                print(f"No vehicle found with role name: {role_name}")
            
            await asyncio.sleep(1)  # Wait for 1 second before the next loop iteration
    except KeyboardInterrupt:
        print("Program terminated by user")  # Handle Ctrl+C interruption

if __name__ == "__main__":
    if args.info:
        try:
            asyncio.get_event_loop().run_until_complete(get_vehicle_info(args.info))
            exit()
        except KeyboardInterrupt:
            print("Program terminated by user. Exiting gracefully.")
            exit(0)
