import argparse
import asyncio
import websockets
import json

# Setting up command line argument parsing to configure the WebSocket server.
# This allows for dynamic IP and port configuration when starting the server.
parser = argparse.ArgumentParser(description='Webserver for handling CARLA vehicle commands.')
parser.add_argument('--w_ip', default='localhost', help='IP address for the WebSocket server.')
parser.add_argument('--w_port', type=int, default=6789, help='Port number for the WebSocket server.')
args = parser.parse_args()

# A set to keep track of connected clients. This is used to manage multiple connections.
connected_clients = set()

# This asynchronous function handles client connections. Each client connection
# is managed in a separate coroutine, allowing for concurrent operations.
async def handle_client(websocket, path):
    # When a new client connects, add them to the set of connected clients.
    connected_clients.add(websocket)
    try:
        # Check if the websocket is still open to ensure we don't process requests from a closed connection.
        if websocket.open:
            print("Client connected.")
        
        # This loop continuously listens for messages from the client.
        async for message in websocket:
            # Decode the JSON message received from the client.
            data = json.loads(message)

            # Process messages based on their type.
            if data["type"] == "set_destination":
                # Broadcast the received message to other clients, excluding the sender.
                tasks = [client.send(message) for client in connected_clients if client != websocket]
                # If there are clients to receive the message, wait until all have received it.
                if tasks:
                    await asyncio.wait(tasks)
                else:
                    print("No other connected clients to send the message to.")
            elif data["type"] == "destination_reached":
                # Prepare and send a notification about the event to all clients.
                notification = json.dumps(data)
                await asyncio.wait([client.send(notification) for client in connected_clients])
    except websockets.exceptions.ConnectionClosedOK:
        # Handle the situation where the client closes the connection gracefully.
        print("Attempted to send a message, but connection was closed normally.")
    except websockets.exceptions.ConnectionClosedError:
        # Handle unexpected client disconnections.
        print("Client disconnected unexpectedly.")
    except websockets.exceptions.WebSocketException as e:
        # General error handling for WebSocket issues.
        print(f"An error occurred while sending a message: {e}")
    finally:
        # Always remove the client from the set of connected clients when they disconnect.
        connected_clients.remove(websocket)

# Start the WebSocket server and bind it to the specified IP and port.
start_server = websockets.serve(handle_client, args.w_ip, args.w_port)
asyncio.get_event_loop().run_until_complete(start_server)

# The server will run indefinitely until it is manually interrupted, typically with a Ctrl+C.
try:
    asyncio.get_event_loop().run_forever()
except KeyboardInterrupt:
    # Handle the case where the program is stopped by the user.
    print("Program terminated by user")
