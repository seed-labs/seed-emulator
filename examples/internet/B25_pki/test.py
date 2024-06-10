import docker

# Create a Docker client
client = docker.from_env()

# Define options
options = {
    'image': 'smallstep/step-cli:0.26.1',  # Docker image to run
    'command': 'ca init --deployment-type "standalone" --name "SEEDEMU Internal" --dns "seedCA.net" --address ":443" --provisioner "admin" --with-ca-url "https://seedCA.net" --password-file /tmp/password.txt --provisioner-password-file /tmp/password.txt --acme',  # Command to execute inside the container
    'detach': True,  # Run the container in detached mode
    'tty': True,  # Allocate a pseudo-TTY
    'stdin_open': True,  # Keep STDIN open even if not attached
    'user': '1000:1000',  # User ID and Group ID
    'environment': {'STEPPATH': '/tmp/.step'},  # Set environment variables
    'entrypoint': 'step',  # Override the default entrypoint
    'volumes': {  # Define volume mappings
        '/tmp/seedemu-ca-x5hbn59z': {'bind': '/tmp', 'mode': 'rw'}
    },
    'remove': True,  # Automatically remove the container when it exits
}

# Run a Docker container with options
container = client.containers.run(**options)

# Print container ID
print(f"Container ID: {container.id}")

# Print container logs
print("Container Logs:")
print(container.logs().decode('utf-8'))
