import hashlib
import json
import sys
from pathlib import Path


def calculate_sha256(filename):
    return hashlib.sha256(
        Path(filename).read_bytes()
    ).hexdigest()


def verify_sensor(measurement_file, metadata_file):

    # Load metadata extracted from the Cardano transaction
    with open(metadata_file, "r") as f:
        metadata = json.load(f)

    # Extract the hash recorded on Cardano
    recorded_hash = metadata["1000"]["data_hash"]

    # Calculate the hash of the received measurement
    calculated_hash = calculate_sha256(measurement_file)

    print("Recorded hash:  ", recorded_hash)
    print("Calculated hash:", calculated_hash)

    if recorded_hash == calculated_hash:
        print("RESULT: VERIFIED")
        return True

    print("RESULT: REJECTED - DATA MODIFIED")
    return False


if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("Usage: python3 verify_sensor.py measurement.json metadata.json")
        sys.exit(2)

    success = verify_sensor(sys.argv[1], sys.argv[2])
    sys.exit(0 if success else 1)
