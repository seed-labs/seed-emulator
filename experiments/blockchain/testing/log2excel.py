#!/usr/bin/env python3
import sys
from datetime import datetime
from openpyxl import Workbook

def parse_line(line):
    line = line.strip()
    if not line or line.startswith("time"):
        return None

    parts = [x.strip() for x in line.split(",")]
    if len(parts) != 4:
        return None

    time, block, mem, cpu = parts
    return [time, int(block), float(mem), float(cpu)]

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 log_to_excel.py input.log")
        return

    input_file = sys.argv[1]
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = f"log_{timestamp}.xlsx"

    wb = Workbook()
    ws = wb.active
    ws.append(["time", "block_number", "mem_usage_GB", "cpu_usage_percent"])

    with open(input_file, "r") as f:
        for line in f:
            row = parse_line(line)
            if row:
                ws.append(row)

    wb.save(output_file)
    print(f"Saved: {output_file}")

if __name__ == "__main__":
    main()

