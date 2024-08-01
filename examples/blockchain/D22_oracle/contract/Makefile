SOLC = solc-8.18

all: oracle

oracle:
	${SOLC} --overwrite --abi --bin -o . Oracle.sol

clean:
	rm -f *.abi *.bin
