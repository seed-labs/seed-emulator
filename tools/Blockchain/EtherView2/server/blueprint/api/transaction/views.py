from web3 import Web3
from datetime import datetime, timedelta
from flask import jsonify, Blueprint, request
from server.utils.models import Transaction

tx = Blueprint('tx', __name__, url_prefix='/tx')


@tx.route('/')
def get_txs():
    page, page_size = int(request.args.get('page', 1)), int(request.args.get('page_size', 50))
    txs = Transaction.query.order_by(Transaction.timestamp.desc()).paginate(page=page, per_page=page_size,
                                                                            error_out=False)
    data = {
        'total': txs.total,
        'txs': [tx.to_dict() for tx in txs.items],
    }
    return jsonify({"data": data, "status": True})


@tx.route('/fees')
def get_tx_fees():
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=24)

    txs = Transaction.query.with_entities(
        Transaction.gasUsed, Transaction.gasPrice
    ).filter(Transaction.timestamp >= hour_ago).all()
    if txs:
        total_fee_wei = sum([tx.gasUsed * tx.gasPrice for tx in txs])
        total_fee_eth = Web3.fromWei(total_fee_wei, 'ether')
        data = {
            'total': len(txs),
            'totalFee': f"{total_fee_eth:.8f} ETH",
            'avgFee': f"{(total_fee_eth / len(txs)):.8f} ETH",
        }
    else:
        data = {
            'total': 0,
            'totalFee': "0 ETH",
            'avgFee': "0 Gwei",
        }

    return jsonify({"data": data, "status": True})
