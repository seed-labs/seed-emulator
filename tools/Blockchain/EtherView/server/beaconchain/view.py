from flask import Flask, Blueprint, render_template, redirect, url_for, flash, current_app as app, request

beaconchain = Blueprint('beaconchain', __name__)

@beaconchain.route("/validator-view/")
def validator_view():
    return render_template("beacon-frontend/validator-view.html")

@beaconchain.route("/slot-view/")
def slot_view():
    return render_template("beacon-frontend/slot-view.html")

@beaconchain.route('/slot-details/<slotNumber>', methods=('GET',))
def getSlotDetails(slotNumber):
    return render_template('beacon-frontend/one-slot.html', slotNumber=slotNumber)




@beaconchain.route('/get_beacon_providers')
def get_beacon_providers():
    providers = []
    for key in app.eth_nodes: 
        node = app.eth_nodes[key]
        providers.append("http://%s:8000" % node['ip'])

    return providers