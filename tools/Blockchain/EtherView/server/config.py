class Config(object):
   NAME     = 'SEED Labs'
   CONSENSUS = 'POA'
   DEFAULT_URL  = 'http://10.154.0.72:8545'
   ETH_NODE_NAME_PATTERN = 'Ethereum-POS'
   DEFAULT_CHAIN_ID = 1337
   CLIENT_WAITING_TIME = 10  # seconds

   KEY_DERIVATION_PATH = "m/44'/60'/0'/0/{}"
   MNEMONIC_PHRASE =  "great amazing fun seed lab protect network system " \
                      "security prevent attack future"
   LOCAL_ACCOUNT_NAMES = ['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank']
