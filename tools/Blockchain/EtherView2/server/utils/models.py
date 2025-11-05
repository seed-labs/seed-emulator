from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()  # 绑定 SQLAlchemy


class Transaction(db.Model):
    __tablename__ = "transaction"  # 表名
    __table_args__ = {"mysql_engine": "InnoDB"}

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True,
        comment="自增主键"
    )
    tx_hash = db.Column(
        db.String(66),
        unique=True,
        nullable=False,
        comment="交易哈希（唯一）"
    )
    block_number = db.Column(
        db.BigInteger,
        nullable=True,
        comment="区块高度"
    )
    status = db.Column(
        db.String(20),
        nullable=True,
        comment="交易状态"
    )
    from_address = db.Column(
        db.String(42),
        nullable=True,
        comment="交易From"
    )
    to_address = db.Column(
        db.String(42),
        nullable=True,
        comment="交易To"
    )
    value = db.Column(
        db.Numeric(30, 18),
        nullable=False,
        comment="Value"
    )
    nonce = db.Column(
        db.Integer,
        nullable=False,
        comment="nonce"
    )
    gasPriceGwei = db.Column(
        db.Numeric(20, 9),
        nullable=True,
        comment='Gas价格（Gwei单位）'
    )
    gasUsed = db.Column(db.BigInteger, nullable=True)
    gasPrice = db.Column(db.BigInteger, nullable=True)
    timestamp = db.Column(
        db.BigInteger,
        nullable=False,
        comment='区块时间戳'
    )
    created_time = db.Column(
        db.DateTime,
        server_default=db.func.current_timestamp(),
        nullable=False,
        comment="记录创建时间"
    )

    def __repr__(self):
        return f"<Transaction id={self.id} tx_hash={self.tx_hash}>"

    def to_dict(self):
        """基础序列化方法"""
        return {
            'id': self.id,
            'hash': self.tx_hash,
            'block_number': self.block_number,
            'from': self.from_address,
            'to': self.to_address,
            'nonce': self.nonce,
            'value': float(self.value) if self.value else 0.0,
            'gasPriceGwei': float(self.gasPriceGwei) if self.gasPriceGwei else None,
            'status': self.status,
            'timestamp': self.timestamp,
            'created_time': self.created_time,
        }
