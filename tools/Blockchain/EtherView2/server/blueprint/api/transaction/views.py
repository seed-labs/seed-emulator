from flask import jsonify, Blueprint, request
from models import Transaction

tx = Blueprint('tx', __name__, url_prefix='/tx')


@tx.route('/')
def get_txs():
    page, page_size = int(request.args.get('page', 1)), int(request.args.get('page_size', 50))
    txs = Transaction.query.order_by(Transaction.timestamp.desc()).paginate(page=page, per_page=page_size, error_out=False)
    data = {
        'total': txs.total,
        'txs': [tx.to_dict() for tx in txs.items],
    }
    return jsonify({"data": data, "status": True})
