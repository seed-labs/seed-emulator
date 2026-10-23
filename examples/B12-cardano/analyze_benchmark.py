#!/usr/bin/env python3

import csv
import glob
import statistics
from pathlib import Path

files = sorted(
    glob.glob("data/performance-test/results/benchmark_*.csv")
)

if not files:
    raise SystemExit("No benchmark results found.")

# Analyze the most recent benchmark.
filename = files[-1]

print(f"\nAnalyzing: {filename}\n")

groups = {
    "baseline": [],
    "metadata": [],
}

with open(filename, newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        if row["status"] == "CONFIRMED_ALL":
            groups[row["type"]].append(row)


def summarize(name, rows):

    if not rows:
        print(f"{name}: no confirmed transactions")
        return

    sizes = [int(r["cbor_size_bytes"]) for r in rows]

    fees = [int(r["fee_lovelace"]) for r in rows]

    confirmations = [
        float(r["confirmation_seconds"])
        for r in rows
    ]

    submissions = [
        float(r["submit_seconds"])
        for r in rows
    ]

    print(f"========== {name.upper()} ==========")

    print("Transactions:", len(rows))

    print(
        "Average transaction size:",
        round(statistics.mean(sizes), 2),
        "bytes"
    )

    print(
        "Average transaction fee:",
        round(statistics.mean(fees), 2),
        "lovelace"
    )

    print(
        "Average submission time:",
        round(statistics.mean(submissions), 4),
        "seconds"
    )

    print(
        "Average confirmation time:",
        round(statistics.mean(confirmations), 4),
        "seconds"
    )

    print(
        "Median confirmation time:",
        round(statistics.median(confirmations), 4),
        "seconds"
    )

    if len(confirmations) >= 2:
        print(
            "Confirmation standard deviation:",
            round(statistics.stdev(confirmations), 4),
            "seconds"
        )

    print(
        "Minimum confirmation:",
        round(min(confirmations), 4),
        "seconds"
    )

    print(
        "Maximum confirmation:",
        round(max(confirmations), 4),
        "seconds"
    )

    print()


summarize("baseline", groups["baseline"])
summarize("metadata", groups["metadata"])
