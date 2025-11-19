from flask import jsonify, Blueprint
from server.utils.etherscan import EtherScan

etherscan = Blueprint('etherscan', __name__, url_prefix='/etherscan')


@etherscan.route('/')
async def get_ether_price():
    home_data = await EtherScan.get_home_data()
    data = home_data
    return jsonify({"data": data, "status": True})
