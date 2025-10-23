import time
import logging
from web3 import Web3
from models import db


class SimpleTransactionMonitor:
    def __init__(self, websocket_url, mysql_config, logger=None):
        self.w3 = Web3(Web3.HTTPProvider(websocket_url))
        self.mysql_config = mysql_config
        self.conn = db.engine.raw_connection()
        self._setup_logging(logger)

    def _setup_logging(self, logger):
        if logger is None:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )
            self.logging = logging
        else:
            self.logging = logger

    def save_transaction(self, tx_hash, status, tx_data):
        """保存交易到数据库"""
        try:
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO transaction
                    (tx_hash, block_number, status, from_address, to_address, value, gasPriceGwei, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    block_number = VALUES(block_number),
                    value = VALUES(value),
                    gasPriceGwei = VALUES(gasPriceGwei),
                    timestamp = VALUES(timestamp),
                    status = VALUES(status);
                """, (
                    tx_hash,
                    tx_data['block_number'],
                    status,
                    tx_data['from'],
                    tx_data['to'],
                    tx_data['value'],
                    tx_data['gasPriceGwei'],
                    tx_data['timestamp'],
                ))
            self.conn.commit()
            self.logging.info(f"保存交易: {tx_hash} - {status}")
        except Exception as e:
            self.logging.error(f"保存交易失败 {tx_hash}: {e}")

    def start_monitoring(self):
        """开始监控"""
        if not self.w3.isConnected():
            self.logging.error("无法连接到区块链节点")
            return

        self.logging.info("开始监控交易...")
        last_block = self.w3.eth.blockNumber
        try:
            while True:
                current_block = self.w3.eth.blockNumber
                self.logging.info(f'{current_block}, {last_block}')
                while current_block > last_block:
                    try:
                        last_block += 1
                        logging.info(f"处理新区块 #{last_block}")

                        # 获取区块详情
                        block = self.w3.eth.getBlock(current_block, full_transactions=True)
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
                                'gasPriceGwei': float(self.w3.fromWei(tx.gasPrice, 'gwei'))
                            }
                            print(tx_data, status, tx.blockNumber)
                            # 保存到数据库
                            self.save_transaction(tx_hash, status, tx_data)
                    except Exception as e:
                        self.logging.info(f"transaction error: {e}")
                time.sleep(2)
        except Exception as e:
            self.logging.info(f"monitor error: {e}")
        finally:
            if self.conn:
                self.conn.close()


def run_tx_monitor(app):
    with app.app_context():
        monitor = SimpleTransactionMonitor(
            websocket_url='http://192.168.254.128:8545',
            # websocket_url='http://10.1.101.81:8545',
            mysql_config={
                'host': 'localhost',
                'user': 'root',
                'password': 'Root@123#',
                'database': 'eth_monitor',
                'charset': 'utf8mb4'
            },
            logger=app.logger
        )
        monitor.start_monitoring()
