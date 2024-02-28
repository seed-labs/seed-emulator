#!/usr/bin/env python3

from typing import Iterable
import sys


def insert_to_df(lines: Iterable[str], host: str, i: int):
    with open(f"./output/hnode_{host}_host_{i}/Dockerfile", "r+") as df:
        o_lines = df.readlines()
        df.seek(0, 0)
        df.writelines(lines)
        o_lines.insert(1, "COPY --from=pre-image /usr/local/bin/op-node /usr/local/bin/op-node\n")
        df.writelines(o_lines)

        
def change_line(host: str, i: int, keyword: str, dst: int):
    with open(f"./output/hnode_{host}_host_{i}/Dockerfile", "r+") as df:
        lines = df.readlines()
        curr = None
        for index, line in enumerate(lines):
            if keyword in line:
                curr = index
                break
        
        if curr is None:
            print("Not found")
            return
        target = lines.pop(curr)
        lines.insert(dst, target)

        df.seek(0,0)
        df.writelines(lines)


def main():
    hosts = range(150, 154)
    ids = range(2)
    
    [change_line(host, i, "sed -i", -2) for host in hosts for i in ids]
    [change_line(host, i, "chmod +x /start_op-", -2) for host in hosts for i in ids]

if __name__ == "__main__":
    main()

