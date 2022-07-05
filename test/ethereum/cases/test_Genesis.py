import unittest
from seedemu.services.EthereumService import *

test_account_file_name = ['UTC--2022-03-25T16-41-21.542086000Z--675eb8226a35256f638712db74878f0a15d3d56e','UTC--2022-04-05T19-21-59.864345000Z--726808f08d63adba50137132a18170de98326c98','UTC--2022-04-05T19-21-56.904952000Z--20cc565f1ac407d24a2a35ab9312cec736880122','UTC--2022-04-05T19-22-01.348137000Z--1a5f6c239ceffb300cdba3031ba4ea5309e60380','UTC--2022-04-05T19-21-58.462119000Z--bb3e9561502ceaed131257765519876a250d374f']

class TestGenesis(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.eth_accounts = []
        for i in range(5):
            with open('../resources/keystore/'+test_account_file_name[i]) as f:
                cls.eth_accounts.append(EthAccount(alloc_balance=999999999,password="admin", keyfile=f.read()))
        return super().setUpClass
    
    def test_init_poa(self) -> None:
        genesisCorrect = '{"config": {"chainId": 10, "homesteadBlock": 0, "eip150Block": 0, "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000", "eip155Block": 0, "eip158Block": 0, "byzantiumBlock": 0, "constantinopleBlock": 0, "petersburgBlock": 0, "istanbulBlock": 0, "clique": {"period": 15, "epoch": 30000}}, "nonce": "0x0", "timestamp": "0x622a4e1a", "extraData": "0x0", "gasLimit": "0x47b760", "difficulty": "0x1", "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000", "coinbase": "0x0000000000000000000000000000000000000000", "alloc": {}, "number": "0x0", "gasUsed": "0x0", "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000", "baseFeePerGas": null}'
        genesis = Genesis(ConsensusMechanism.POA)
        self.assertEqual(str(genesis),genesisCorrect)

    def test_init_pow(self) -> None: 
        genesisCorrect = '{"nonce": "0x0", "timestamp": "0x621549f1", "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000", "extraData": "0x", "gasLimit": "0x80000000", "difficulty": "0x0", "mixhash": "0x0000000000000000000000000000000000000000000000000000000000000000", "coinbase": "0x0000000000000000000000000000000000000000", "number": "0x0", "gasUsed": "0x0", "baseFeePerGas": null, "config": {"chainId": 10, "homesteadBlock": 0, "eip150Block": 0, "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000", "eip155Block": 0, "eip158Block": 0, "byzantiumBlock": 0, "constantinopleBlock": 0, "petersburgBlock": 0, "istanbulBlock": 0, "ethash": {}}, "alloc": {}}'
        genesis = Genesis(ConsensusMechanism.POW)
        self.assertEqual(str(genesis),genesisCorrect)

    def test_allocateBalance_POW(self) -> None:
        genesisCorrect = '{"nonce": "0x0", "timestamp": "0x621549f1", "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000", "extraData": "0x", "gasLimit": "0x80000000", "difficulty": "0x0", "mixhash": "0x0000000000000000000000000000000000000000000000000000000000000000", "coinbase": "0x0000000000000000000000000000000000000000", "number": "0x0", "gasUsed": "0x0", "baseFeePerGas": null, "config": {"chainId": 10, "homesteadBlock": 0, "eip150Block": 0, "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000", "eip155Block": 0, "eip158Block": 0, "byzantiumBlock": 0, "constantinopleBlock": 0, "petersburgBlock": 0, "istanbulBlock": 0, "ethash": {}}, "alloc": {"675eB8226a35256F638712Db74878f0A15d3D56E": {"balance": "999999999"}, "726808F08d63ADBa50137132a18170dE98326c98": {"balance": "999999999"}, "20cc565f1ac407d24a2a35AB9312cEC736880122": {"balance": "999999999"}, "1a5F6c239CeFfb300CDbA3031Ba4Ea5309E60380": {"balance": "999999999"}, "BB3E9561502ceaED131257765519876A250D374F": {"balance": "999999999"}}}'
        genesis = Genesis(ConsensusMechanism.POW)
        genesis.allocateBalance(self.eth_accounts)
        self.assertEqual(str(genesis),genesisCorrect)
    
    def test_allocateBalance_POA(self) -> None:
        genesisCorrect = '{"config": {"chainId": 10, "homesteadBlock": 0, "eip150Block": 0, "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000", "eip155Block": 0, "eip158Block": 0, "byzantiumBlock": 0, "constantinopleBlock": 0, "petersburgBlock": 0, "istanbulBlock": 0, "clique": {"period": 15, "epoch": 30000}}, "nonce": "0x0", "timestamp": "0x622a4e1a", "extraData": "0x0", "gasLimit": "0x47b760", "difficulty": "0x1", "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000", "coinbase": "0x0000000000000000000000000000000000000000", "alloc": {"675eB8226a35256F638712Db74878f0A15d3D56E": {"balance": "999999999"}, "726808F08d63ADBa50137132a18170dE98326c98": {"balance": "999999999"}, "20cc565f1ac407d24a2a35AB9312cEC736880122": {"balance": "999999999"}, "1a5F6c239CeFfb300CDbA3031Ba4Ea5309E60380": {"balance": "999999999"}, "BB3E9561502ceaED131257765519876A250D374F": {"balance": "999999999"}}, "number": "0x0", "gasUsed": "0x0", "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000", "baseFeePerGas": null}'
        genesis = Genesis(ConsensusMechanism.POA)
        genesis.allocateBalance(self.eth_accounts)
        self.assertEqual(str(genesis),genesisCorrect)
        
    def test_setSealer_POW(self) -> None:
        genesisCorrect = '{"nonce": "0x0", "timestamp": "0x621549f1", "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000", "extraData": "0x0000000000000000000000000000000000000000000000000000000000000000675eB8226a35256F638712Db74878f0A15d3D56E726808F08d63ADBa50137132a18170dE98326c9820cc565f1ac407d24a2a35AB9312cEC7368801221a5F6c239CeFfb300CDbA3031Ba4Ea5309E60380BB3E9561502ceaED131257765519876A250D374F0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", "gasLimit": "0x80000000", "difficulty": "0x0", "mixhash": "0x0000000000000000000000000000000000000000000000000000000000000000", "coinbase": "0x0000000000000000000000000000000000000000", "number": "0x0", "gasUsed": "0x0", "baseFeePerGas": null, "config": {"chainId": 10, "homesteadBlock": 0, "eip150Block": 0, "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000", "eip155Block": 0, "eip158Block": 0, "byzantiumBlock": 0, "constantinopleBlock": 0, "petersburgBlock": 0, "istanbulBlock": 0, "ethash": {}}, "alloc": {}}'
        genesis = Genesis(ConsensusMechanism.POW)
        genesis.setSigner(self.eth_accounts)
        self.assertEqual(str(genesis),genesisCorrect)

    def test_setSealer_POA(self) -> None:
        genesisCorrect = '{"config": {"chainId": 10, "homesteadBlock": 0, "eip150Block": 0, "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000", "eip155Block": 0, "eip158Block": 0, "byzantiumBlock": 0, "constantinopleBlock": 0, "petersburgBlock": 0, "istanbulBlock": 0, "clique": {"period": 15, "epoch": 30000}}, "nonce": "0x0", "timestamp": "0x622a4e1a", "extraData": "0x0000000000000000000000000000000000000000000000000000000000000000675eB8226a35256F638712Db74878f0A15d3D56E726808F08d63ADBa50137132a18170dE98326c9820cc565f1ac407d24a2a35AB9312cEC7368801221a5F6c239CeFfb300CDbA3031Ba4Ea5309E60380BB3E9561502ceaED131257765519876A250D374F0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", "gasLimit": "0x47b760", "difficulty": "0x1", "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000", "coinbase": "0x0000000000000000000000000000000000000000", "alloc": {}, "number": "0x0", "gasUsed": "0x0", "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000", "baseFeePerGas": null}'
        genesis = Genesis(ConsensusMechanism.POA)
        genesis.setSigner(self.eth_accounts)
        self.assertEqual(str(genesis),genesisCorrect)
    
    def test_allocate_balance_and_setSealer_POW(self) -> None:
        genesisCorrect = '{"nonce": "0x0", "timestamp": "0x621549f1", "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000", "extraData": "0x0000000000000000000000000000000000000000000000000000000000000000675eB8226a35256F638712Db74878f0A15d3D56E726808F08d63ADBa50137132a18170dE98326c9820cc565f1ac407d24a2a35AB9312cEC7368801221a5F6c239CeFfb300CDbA3031Ba4Ea5309E60380BB3E9561502ceaED131257765519876A250D374F0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", "gasLimit": "0x80000000", "difficulty": "0x0", "mixhash": "0x0000000000000000000000000000000000000000000000000000000000000000", "coinbase": "0x0000000000000000000000000000000000000000", "number": "0x0", "gasUsed": "0x0", "baseFeePerGas": null, "config": {"chainId": 10, "homesteadBlock": 0, "eip150Block": 0, "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000", "eip155Block": 0, "eip158Block": 0, "byzantiumBlock": 0, "constantinopleBlock": 0, "petersburgBlock": 0, "istanbulBlock": 0, "ethash": {}}, "alloc": {"675eB8226a35256F638712Db74878f0A15d3D56E": {"balance": "999999999"}, "726808F08d63ADBa50137132a18170dE98326c98": {"balance": "999999999"}, "20cc565f1ac407d24a2a35AB9312cEC736880122": {"balance": "999999999"}, "1a5F6c239CeFfb300CDbA3031Ba4Ea5309E60380": {"balance": "999999999"}, "BB3E9561502ceaED131257765519876A250D374F": {"balance": "999999999"}}}'
        genesis = Genesis(ConsensusMechanism.POW)
        genesis.allocateBalance(self.eth_accounts)
        genesis.setSigner(self.eth_accounts)
        self.assertEqual(str(genesis),genesisCorrect)
    
    def test_allocate_balance_and_setSealer_POA(self) -> None:
        genesisCorrect = '{"config": {"chainId": 10, "homesteadBlock": 0, "eip150Block": 0, "eip150Hash": "0x0000000000000000000000000000000000000000000000000000000000000000", "eip155Block": 0, "eip158Block": 0, "byzantiumBlock": 0, "constantinopleBlock": 0, "petersburgBlock": 0, "istanbulBlock": 0, "clique": {"period": 15, "epoch": 30000}}, "nonce": "0x0", "timestamp": "0x622a4e1a", "extraData": "0x0000000000000000000000000000000000000000000000000000000000000000675eB8226a35256F638712Db74878f0A15d3D56E726808F08d63ADBa50137132a18170dE98326c9820cc565f1ac407d24a2a35AB9312cEC7368801221a5F6c239CeFfb300CDbA3031Ba4Ea5309E60380BB3E9561502ceaED131257765519876A250D374F0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", "gasLimit": "0x47b760", "difficulty": "0x1", "mixHash": "0x0000000000000000000000000000000000000000000000000000000000000000", "coinbase": "0x0000000000000000000000000000000000000000", "alloc": {"675eB8226a35256F638712Db74878f0A15d3D56E": {"balance": "999999999"}, "726808F08d63ADBa50137132a18170dE98326c98": {"balance": "999999999"}, "20cc565f1ac407d24a2a35AB9312cEC736880122": {"balance": "999999999"}, "1a5F6c239CeFfb300CDbA3031Ba4Ea5309E60380": {"balance": "999999999"}, "BB3E9561502ceaED131257765519876A250D374F": {"balance": "999999999"}}, "number": "0x0", "gasUsed": "0x0", "parentHash": "0x0000000000000000000000000000000000000000000000000000000000000000", "baseFeePerGas": null}'
        genesis = Genesis(ConsensusMechanism.POA)
        genesis.allocateBalance(self.eth_accounts)
        genesis.setSigner(self.eth_accounts)
        # print(genesis)
        self.assertEqual(str(genesis),genesisCorrect)
    
if __name__ == '__main__':
    unittest.main()
