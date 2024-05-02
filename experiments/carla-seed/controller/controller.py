#!/usr/bin/env python3
import argparse
import carla
import asyncio
import websockets
import json
import math

# Set up command line arguments to configure servers and vehicle interaction details
parser = argparse.ArgumentParser(description="Controller with customizable WebSocket IP/Port and optional location")
parser.add_argument("--w_ip", default="localhost", help="IP address of the WebSocket server")
parser.add_argument("--w_port", default="6789", help="Port number of the WebSocket server")
parser.add_argument("--c_ip", default="localhost", help="IP address of the CARLA server")
parser.add_argument("--c_port", default=2000, type=int, help="Port number of the CARLA server")
parser.add_argument("--location", default="Townhall", help="Name of the predefined location to set as the destination (Townhall, Museum, Hotel, Basketballcourt, Skateboardpark)")
parser.add_argument("--id", default="all", help="Identifier for the car to send the location, or 'all' to send to all cars")
parser.add_argument("--list", action="store_true", help="List all car role names and exit")
parser.add_argument("--c_info", help="Get detailed info for a car based on its role name")

args = parser.parse_args()

# Construct WebSocket URI from command-line arguments
WEBSOCKET_URI = f"ws://{args.w_ip}:{args.w_port}"

async def set_destination(location_name, id="all"):
    # Send destination settings to the WebSocket server. This will be broadcast to all connected clients.
    try:
        destination = {"type": "set_destination", "location_name": location_name, "car_id": id}
        async with websockets.connect(WEBSOCKET_URI) as websocket:
            await websocket.send(json.dumps(destination))
            print(f"Setting destination to {location_name} for role {id}")
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed unexpectedly: {e}")
    except ConnectionRefusedError:
        print("Connection to the WebSocket server failed.")

async def receive_notifications():
    # Listen for notifications from the WebSocket server. 
    try:
        async with websockets.connect(WEBSOCKET_URI) as websocket:
            async for message in websocket:
                data = json.loads(message)
                if data.get("message") is not None and "None" not in data["message"]:
                    if data["type"] == "destination_reached":
                        print(data["message"])

    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed unexpectedly: {e}")
    except ConnectionRefusedError:
        print("Is the server running?")


def get_vehicle_roles():
    #Retrieve all vehicle actors and print their role names
    client = carla.Client(args.c_ip, args.c_port)
    client.set_timeout(10.0)
    world = client.get_world()
    vehicle_actors = world.get_actors().filter('vehicle.*')

    for vehicle in vehicle_actors:
        role_name = vehicle.attributes.get('role_name', 'Unknown')
        if role_name.startswith('seed'):
            print(f"Vehicle {vehicle.id} with role: {role_name}")

async def get_vehicle_info(role_name):
    # Get detailed information about a vehicle based on its role name
    client = carla.Client(args.c_ip, args.c_port)
    client.set_timeout(10.0)
    world = client.get_world()   
    try:
        while True:
            vehicle_actors = world.get_actors().filter('vehicle.*')
            found = False
            for vehicle in vehicle_actors:
                # Check if the vehicle matches the specified role name
                if vehicle.attributes.get('role_name', '') == args.c_info:
                    # Get vehicle location
                    location = vehicle.get_location()
                    location_str = f"({location.x:.2f}, {location.y:.2f}, {location.z:.2f})"
                    
                    # Get vehicle speed (in km/h)
                    velocity = vehicle.get_velocity()
                    speed_kmh = 3.6 * math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)  # Convert m/s to km/h
                    controls = vehicle.get_control()
                    
                    # Get the vehicle type (model)
                    car_type = vehicle.type_id

                    print(f"Vehicle ID: {vehicle.id} with role: {role_name}")
                    print(f"Location: {location_str}")
                    print(f"Speed: {speed_kmh:.2f} km/h")
                    print(f"Car Type: {car_type}")
                    print(f"Throttle: {controls.throttle:.2f},\nBrake: {controls.brake:.2f},\nSteer: {controls.steer:.2f},\nReverse: {controls.reverse},\nHand Brake: {controls.hand_brake}\n")
                    found = True

                    # Assuming you only need info for the first vehicle that matches the role name
                    break
            if not found:
                # This else block executes if no vehicle matching the role name is found in the loop
                print(f"No vehicle found with role name: {role_name}")
            
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Program terminated by user")

if __name__ == "__main__":
    if args.list:
        get_vehicle_roles()
        exit()
    # Check if the user has requested detailed info for a specific car based on its role name.
    if args.c_info:
        try:
            asyncio.get_event_loop().run_until_complete(get_vehicle_info(args.c_info))
            exit()
        except KeyboardInterrupt:
            #Handle the KeyboardInterrupt (typically triggered by Ctrl+C) gracefully by exiting.
            print("Program terminated by user. Exiting gracefully.")
            exit(0)
    # Dictionary mapping predefined location names to coordinates.
    # These locations are specific points that can be used as destinations in the CARLA simulation.
    locations = {
        "Townhall": (112.70506286621094, 9.616304397583008, 0.6047301888465881),
        "Museum": (-115.36235046386719, 11.285353660583496, 1.249739170074463),
        "Hotel": (-3.092482805252075, -67.59429931640625, 0.872872531414032),
        "Basketballcourt": (-40.11349105834961, 109.1531982421875, 0.16197647154331207),
        "Skateboardpark": (-89.92167663574219, 131.5748748779297, 1.4565911293029785)
    }

    
    location_name = args.location
    # Check if a valid location name is provided and if it exists in the predefined locations.
    if args.location and args.location in locations:
        try:
            # If valid, set the destination and listen for notifications.
            # These asynchronous tasks manage setting the destination in CARLA and receiving acknowledgment.
            asyncio.get_event_loop().run_until_complete(set_destination(location_name, args.id))
            asyncio.get_event_loop().run_until_complete(receive_notifications())
        except KeyboardInterrupt:
            # Handle KeyboardInterrupt during the async operations to gracefully terminate the program.
            print("Program terminated by user")
    else:
        # If an invalid location is specified, print an error message and exit the script.
        print("Invalid location name provided or no location name provided. Exiting.")
