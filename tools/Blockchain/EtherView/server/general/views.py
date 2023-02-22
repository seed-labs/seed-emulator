from flask import Flask, Blueprint, render_template, redirect, url_for, flash, current_app as app, request

import os, json

general = Blueprint('general', __name__)

@general.route("/")
def home_index():
    return render_template('index.html')
    
@general.route("/account-view/")
def account_view():
    emulator_parameters = {}
    emulator_parameters["web3_provider"]  = app.web3_url
    emulator_parameters["client_waiting_time"]  = app.configure['client_waiting_time']
    return render_template('general-frontend/account-view.html', data = emulator_parameters)

@general.route("/block-view/")
def block_view():
    emulator_parameters = {}
    emulator_parameters["web3_provider"]  = app.web3_url
    emulator_parameters["client_waiting_time"]  = app.configure['client_waiting_time']
    return render_template('general-frontend/block-view.html', data = emulator_parameters)


@general.route('/block/<blockNumber>')
def block(blockNumber):
    emulator_parameters = {}
    emulator_parameters["web3_provider"]  = app.web3_url
    emulator_parameters["block_number"]  = blockNumber
    return render_template('general-frontend/one_block.html', data = emulator_parameters)

@general.route('/tx/<txHash>')
def transaction(txHash):
    emulator_parameters = {}
    emulator_parameters["web3_provider"]  = app.web3_url
    emulator_parameters["tx_hash"]  = txHash
    return render_template('general-frontend/one_tx.html', data = emulator_parameters)

@general.route('/txpool/')
def txpool():
    return render_template('general-frontend/txpool.html')