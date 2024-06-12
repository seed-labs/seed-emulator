SOLC = ../../solc-8.18

all: seedtoken20

seedtoken20:
	${SOLC} --overwrite --abi --bin -o . SEEDToken20.sol

clean:
	rm -f *.abi *.bin
