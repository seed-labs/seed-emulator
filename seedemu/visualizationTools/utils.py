import socket


def find_free_ports(
    port_range: tuple[int, int],
    count: int,
    host: str = "0.0.0.0",
) -> list[int]:
    """
    Search for the first count available TCP ports within the specified port range.

    :param port_range:  (8000, 9999)
    :param count: 
    :param host: default 0.0.0.0
    :return: 
    """
    start_port, end_port = port_range
    free_ports: list[int] = []

    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
                free_ports.append(port)

                if len(free_ports) >= count:
                    break
            except OSError:
                pass

    return free_ports