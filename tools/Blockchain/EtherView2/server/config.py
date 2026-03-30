import logging
from urllib.parse import quote_plus


class Config(object):
    NAME = 'SEED Labs'
    CONSENSUS = 'POA'
    DEFAULT_URL = 'http://10.154.0.72:8545'
    ETH_NODE_NAME_PATTERN = 'Ethereum-POS'
    DEFAULT_CHAIN_ID = 1337
    CLIENT_WAITING_TIME = 10  # seconds

    KEY_DERIVATION_PATH = "m/44'/60'/0'/0/{}"
    MNEMONIC_PHRASE = "great amazing fun seed lab protect network system " \
                      "security prevent attack future"
    LOCAL_ACCOUNT_NAMES = ['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank']

    # frontend
    URL_PREFIX = '/frontend'
    STATIC_ASSET_PREFIX = '/static'
    FRONTEND_DIST_DIR = 'static/frontend'

    # mysql
    DB_HOST = 'localhost'
    DB_PORT = 3306
    DB_USER = 'root'
    DB_PASSWORD = '123456'
    DB_NAME = 'eth_monitor'
    # 使用 Flask‑SQLAlchemy 时的 URI 写法
    SQLALCHEMY_DATABASE_URI = (
        f'mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    )
    # 关闭 SQLAlchemy 的事件系统（可选，提升性能）
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # log
    LOG_LEVEL = logging.INFO
    LOG_FILE = 'logs/server.log'
