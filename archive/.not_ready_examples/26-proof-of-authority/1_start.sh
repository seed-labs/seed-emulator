sudo rm -rf base-component.bin component-blockchain.bin emulator
sleep 3
./nano-internet.py
sleep 3
./component-blockchain.py
sleep 3
./blockchain.py
sleep 3
(cd emulator && docker-compose build && docker-compose up)
