import time
import logging
from web3 import Web3
from server.utils.models import db


class SimpleTransactionMonitor:
    def __init__(self, websocket_url, mysql_config, logger=None):
        self.w3 = Web3(Web3.HTTPProvider(websocket_url))
        self.mysql_config = mysql_config
        self.conn = db.engine.raw_connection()
        self._setup_logging(logger)
        self.init_data_total = 100

    def _setup_logging(self, logger):
        if logger is None:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
            self.logging = logging
        else:
            self.logging = logger

    def _save_transaction(self, data_list):
        """保存交易到数据库"""
        try:
            with self.conn.cursor() as cursor:
                cursor.executemany("""
                    INSERT INTO transaction
                    (tx_hash, block_number, status, from_address, to_address, value, nonce, gasPriceGwei, gasPrice, gasUsed, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    block_number = VALUES(block_number),
                    value = VALUES(value),
                    nonce = VALUES(nonce),
                    gasPriceGwei = VALUES(gasPriceGwei),
                    timestamp = VALUES(timestamp),
                    gasPrice = VALUES(gasPrice),
                    gasUsed = VALUES(gasUsed),
                    status = VALUES(status);
                """, data_list)
            self.conn.commit()
            self.logging.debug(f"save success: {data_list}")
            self.logging.info("save success")
        except Exception as e:
            self.logging.error(f"save failed : {e}")

    def start_monitoring(self):
        """开始监控"""
        for i in range(3):
            if self.w3.isConnected():
                break
            self.logging.error("connect web3 failed")
            time.sleep(5)
            if i == 2:
                return
        self.logging.info("start_monitoring...")
        last_block = self.w3.eth.blockNumber
        self._init_data(last_block)
        try:
            while True:
                current_block = self.w3.eth.blockNumber
                while current_block > last_block:
                    try:
                        last_block += 1
                        self.logging.info(f"deal new block #{last_block}")
                        txs = self._get_tx_by_block_number(current_block)
                        if not txs:
                            continue
                        self._save_transaction(txs)
                    except Exception as e:
                        self.logging.info(f"transaction error: {e}")
                time.sleep(2)
        except Exception as e:
            self.logging.info(f"monitor error: {e}")
        finally:
            if self.conn:
                self.conn.close()

    def _get_tx_by_block_number(self, block_number):
        # 获取区块详情
        block = self.w3.eth.getBlock(block_number, full_transactions=True)
        txs = []
        # 处理区块中的每笔交易
        for tx in block.transactions:
            tx_hash = tx.hash.hex()
            # 获取交易状态
            receipt = self.w3.eth.getTransactionReceipt(tx.hash)
            if receipt:
                status = "success" if receipt.status == 1 else "failed"
            else:
                status = "pending"
            # 准备交易数据
            tx_data = {
                'block_number': tx.blockNumber,
                'timestamp': block.timestamp,
                'from': tx['from'],
                'to': tx['to'],
                'nonce': tx.nonce,
                'value': float(self.w3.fromWei(tx.value, 'ether')),
                'gasPriceGwei': float(self.w3.fromWei(tx.gasPrice, 'gwei')),
                'gasPrice': tx.gasPrice,
                'gasUsed': receipt.gasUsed,
            }
            txs.append(
                (tx_hash,
                 tx_data['block_number'],
                 status,
                 tx_data['from'],
                 tx_data['to'],
                 tx_data['value'],
                 tx_data['nonce'],
                 tx_data['gasPriceGwei'],
                 tx_data['gasPrice'],
                 tx_data['gasUsed'],
                 tx_data['timestamp'])
            )
        return txs

    def _init_data(self, last_block_number):
        start = last_block_number - self.init_data_total
        if start < 0:
            start = 0
        for i in range(start, last_block_number + 1):
            txs = self._get_tx_by_block_number(i)
            if not txs:
                continue
            self._save_transaction(txs)


def run_tx_monitor(app):
    with app.app_context():
        monitor = SimpleTransactionMonitor(
            websocket_url=app.web3_url,
            mysql_config={
                'host': app.config.get('DB_HOST', 'localhost'),
                'port': app.config.get('DB_PORT', 3306),
                'user': app.config.get('DB_USER', 'root'),
                'password': app.config.get('DB_PASSWORD', 'Root@123#'),
                'database': app.config.get('DB_DATABASE', 'eth_monitor'),
                'charset': 'utf8mb4'
            },
            logger=app.logger
        )
        monitor.start_monitoring()
