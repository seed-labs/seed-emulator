from typing import Dict

GethCommandTemplates: Dict[str, str] = {}

GethCommandTemplates['base'] = '''\
geth --datadir {datadir} --identity="NODE_{node_id}" --networkid={chain_id} --syncmode {syncmode}\
 --snapshot={snapshot} --verbosity=2 --allow-insecure-unlock --port 30303\
{option[finding_peers]}\
{option[http]}\
{option[ws]}\
{option[pos]}\
{option[unlock]}\
                            {option[mine]}'''


GethCommandTemplates['mine'] = '''\
 --miner.etherbase "{coinbase}" --mine --miner.threads={num_of_threads}'''

GethCommandTemplates['unlock'] = '''\
 --unlock "{accounts}" --password "/tmp/eth-password"'''

GethCommandTemplates['http'] = '''\
 --http --http.addr 0.0.0.0 --http.port {gethHttpPort} --http.corsdomain "*" --http.api web3,eth,debug,personal,net,clique,engine,admin,txpool'''

GethCommandTemplates['ws'] = '''\
 --ws --ws.addr 0.0.0.0 --ws.port {gethWsPort} --ws.origins "*" --ws.api web3,eth,debug,personal,net,clique,engine,admin,txpool'''

GethCommandTemplates['pos'] = '''\
 --authrpc.addr 0.0.0.0 --authrpc.port 8551 --authrpc.vhosts "*" --authrpc.jwtsecret /tmp/jwt.hex --override.terminaltotaldifficulty {difficulty}'''

GethCommandTemplates['nodiscover'] = '''\
 --nodiscover'''

GethCommandTemplates['bootnodes'] = '''\
 --bootnodes "$(cat /tmp/eth-node-urls)"'''

