#!/usr/bin/env python3
"""Automate native-ADA transactions on a private Cardano Conway Docker testnet.
Python 3.8+, standard library only. No private signing keys enter containers.
"""
import argparse
import csv
import hashlib
import shutil
import datetime as dt
import json
import re
import subprocess
import sys
import time
import uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path

DEFAULT_NODES = {str(a): 'as{}h-Cardano-Node-{}-10.{}.0.71'.format(a, a-149, a) for a in range(150,154)}
FIELDS = ['metadata_file','metadata_sha256','run_id','utc_started','utc_finished','status','submit_node','sender','receiver','amount_ada','amount_lovelace','inputs','txhash','fee_lovelace_estimated','submit_seconds','confirmation_seconds','confirmed_nodes','error']

class Failure(Exception): pass

def run(args, timeout=45):
    try:
        p = subprocess.run([str(s) for s in args], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Failure('{}: {}'.format(' '.join(map(str,args[:4])), e)) from e
    if p.returncode:
        raise Failure('Command failed: {}\n{}'.format(' '.join(map(str,args)), (p.stderr or p.stdout).strip()))
    return p.stdout.strip()

def remote(node, *cli_args, timeout=45):
    return run(['docker','exec',node,'cardano-cli',*cli_args,'--testnet-magic','4242',
                '--socket-path','/cardano/node.socket'], timeout=timeout)

def utxos(node, address):
    # cli query utxo gives JSON in tested node version; --out-file not required
    return json.loads(remote(node,'query','utxo','--address',address))

def resolve_address(value, data_dir):
    if value.isdecimal() and 1 <= int(value) <= 99:
        path = data_dir / ('delegator{}-base.addr'.format(value))
        if not path.is_file(): raise Failure('Address file missing: {}'.format(path))
        value = path.read_text().strip()
    elif Path(value).is_file():
        value = Path(value).read_text().strip()
    if not re.fullmatch(r'addr_test1[023456789acdefghjklmnpqrstuvwxyz]+', value):
        raise Failure('Expected a testnet Bech32 address (or delegator index/address file).')
    return value

def resolve_key(sender_arg, key_arg, keys_root):
    if key_arg: path = Path(key_arg)
    elif sender_arg.isdecimal(): path = keys_root / ('delegator{}/payment.skey'.format(sender_arg))
    else: raise Failure('With a custom sender address, --signing-key is required.')
    if not path.is_file(): raise Failure('Signing key missing: {}'.format(path))
    return path

def parse_amount(x):
    try: a = Decimal(x)
    except InvalidOperation as e: raise Failure('Invalid ADA amount') from e
    if not a.is_finite() or a <= 0 or a.as_tuple().exponent < -6:
        raise Failure('Amount must be positive, with at most six decimal places.')
    love = a * 1000000
    if love != love.to_integral_value(): raise Failure('ADA amount must be whole lovelace.')
    return int(love)

def parse_txhash(output):
    """Accept CLI txid output as either plain hex or {"txhash": "..."}."""
    value = output.strip()
    if value.startswith('{'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as e:
            raise Failure('Invalid txid JSON: {}'.format(value)) from e
        if not isinstance(parsed, dict):
            raise Failure('Unexpected txid response: {}'.format(value))
        value = parsed.get('txhash', '')
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', value):
        raise Failure('Unexpected txid: {}'.format(output.strip()))
    return value.lower()


def validate_metadata(path):
    """Validate JSON and Cardano transaction-metadatum restrictions before build."""
    try:
        with path.open('r', encoding='utf-8') as f:
            doc = json.load(f, parse_float=lambda x: (_ for _ in ()).throw(Failure(
                'Metadata cannot contain floating-point values: ' + x)))
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        raise Failure('Invalid metadata JSON: {}'.format(e)) from e
    if not isinstance(doc, dict) or not doc:
        raise Failure('Metadata must be a nonempty object of numeric labels.')
    for label in doc:
        if not label.isdecimal() or not 0 <= int(label) < 2**64:
            raise Failure('Metadata label must be an unsigned 64-bit integer: ' + repr(label))
    def check(value, where):
        if value is None or isinstance(value, bool):
            raise Failure('No null/boolean metadata values at ' + where)
        if isinstance(value, str):
            if len(value.encode('utf-8')) > 64:
                raise Failure('Metadata text exceeds 64 UTF-8 bytes at ' + where)
        elif isinstance(value, int):
            if not -(2**64) <= value < 2**64:
                raise Failure('Metadata integer outside supported range at ' + where)
        elif isinstance(value, list):
            for n, item in enumerate(value): check(item, where + '[' + str(n) + ']')
        elif isinstance(value, dict):
            for key, item in value.items():
                check(key, where + '.key')
                check(item, where + '.' + key)
        else:
            raise Failure('Unsupported metadata value at ' + where)
    for label, item in doc.items(): check(item, label)
    return doc


def save_record(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)

    # Upgrade old CSV headers without discarding existing experiment history.
    if path.exists() and path.stat().st_size:
        with path.open(newline='') as f:
            reader = csv.DictReader(f)
            old_fields = reader.fieldnames or []

            if old_fields != FIELDS:
                old_records = list(reader)
                temp = path.with_suffix('.csv.upgrading')

                with temp.open('w', newline='') as f2:
                    w = csv.DictWriter(
                        f2,
                        fieldnames=FIELDS,
                        extrasaction='ignore'
                    )
                    w.writeheader()

                    for old in old_records:
                        w.writerow(old)

                temp.replace(path)

    # Append the new experiment result.
    with path.open('a', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=FIELDS)

        if f.tell() == 0:
            wr.writeheader()

        csv_record = {k: record.get(k, '') for k in FIELDS}

        if isinstance(csv_record.get('confirmed_nodes'), dict):
            csv_record['confirmed_nodes'] = json.dumps(
                csv_record['confirmed_nodes'],
                sort_keys=True
            )

        wr.writerow(csv_record)

def main():
    ap = argparse.ArgumentParser(description='Build/sign/submit/confirm Cardano Conway ADA transfer via any Docker node')
    ap.add_argument('--node', default='150', help='submit node: AS number 150..153 or Docker container name')
    ap.add_argument('--from', dest='sender', required=True, help='delegator index, .addr file, or addr_test1...')
    ap.add_argument('--to', dest='receiver', required=True, help='delegator index, .addr file, or addr_test1...')
    ap.add_argument('--amount', required=True, help='ADA amount, e.g. 100 or 0.5')
    ap.add_argument('--metadata', help='Cardano metadata JSON file (optional)')
    ap.add_argument('--signing-key', help='payment.skey path (required for custom sender)')
    ap.add_argument('--data-dir', default='data/transaction-test')
    ap.add_argument('--keys-root', default='config/generated/testnet-02/stake-delegators')
    ap.add_argument('--cli', default='./resources/cardano-static/bin/cardano-cli')
    ap.add_argument('--verify-nodes', nargs='*', default=['150','151','152','153'], help='AS numbers or container names; empty means submission node only')
    ap.add_argument('--timeout', type=int, default=180, help='seconds to wait for confirmation (default 180)')
    ap.add_argument('--interval', type=float, default=3, help='poll interval in seconds')
    ap.add_argument('--network-magic', type=int, default=4242)
    ap.add_argument('--execute', action='store_true', help='ACTUALLY sign and submit; without this, build only')
    args = ap.parse_args()
    # Network magic is passed explicitly to every query/build/sign/submit below.
    global remote
    def remote_configured(node, *cli_args, timeout=45):
        return run(['docker','exec',node,'cardano-cli',*cli_args,'--testnet-magic',str(args.network_magic),
                    '--socket-path','/cardano/node.socket'], timeout=timeout)
    remote = remote_configured
    data = Path(args.data_dir)
    node = DEFAULT_NODES.get(args.node,args.node)
    peers = [DEFAULT_NODES.get(x,x) for x in (args.verify_nodes or [args.node])]
    if node not in peers: peers.insert(0,node)
    started = dt.datetime.now(dt.timezone.utc)
    runid = started.strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:8]
    folder = data/'runs'/runid
    folder.mkdir(parents=True,exist_ok=False)
    record = dict(run_id=runid, utc_started=started.isoformat(), status='started', submit_node=node,
                  sender=args.sender,receiver=args.receiver,amount_ada=args.amount)
    csv_file = data/'transaction_history.csv'
    try:
        if args.timeout <= 0 or args.interval <= 0: raise Failure('Timeout and interval must be positive')
        src = resolve_address(args.sender,data); dst = resolve_address(args.receiver,data)
        if src == dst: raise Failure('Sender and receiver must differ for this experiment.')
        love = parse_amount(args.amount)
        record.update(sender=src,receiver=dst,amount_lovelace=love)
        key = resolve_key(args.sender,args.signing_key,Path(args.keys_root))
        if not Path(args.cli).is_file(): raise Failure('Local cardano-cli not found: {}'.format(args.cli))
        tip = json.loads(remote(node,'query','tip'))
        if tip.get('era','').lower() != 'conway': raise Failure('Node era is {}, expected Conway'.format(tip.get('era')))
        entries = utxos(node,src)
        # Pure ADA UTxOs only: avoids accidentally consuming tokens and special script outputs.
        candidates = sorted([(ref,int(v['value']['lovelace'])) for ref,v in entries.items()
             if isinstance(v.get('value'),dict) and set(v['value']) == {'lovelace'} and int(v['value']['lovelace'])>0],
             key=lambda t: t[1],reverse=True)
        selected=[]; total=0
        for ref,amount in candidates:
            selected.append(ref);total+=amount
            if total >= love + 3000000: break # conservative surplus for change and fees
        if total < love+3000000: raise Failure('Insufficient pure ADA UTxOs (need amount + 3 ADA reserve): {} lovelace'.format(total))
        record['inputs']=';'.join(selected)
        metadata_container = None
        if args.metadata:
            source_metadata = Path(args.metadata)
            if not source_metadata.is_file():
                raise Failure('Metadata file not found: {}'.format(source_metadata))
            validate_metadata(source_metadata)
            saved_metadata = folder / 'metadata.json'
            shutil.copyfile(str(source_metadata), str(saved_metadata))
            record['metadata_file'] = str(saved_metadata)
            record['metadata_sha256'] = hashlib.sha256(saved_metadata.read_bytes()).hexdigest()
            metadata_container = '/tmp/{}.metadata.json'.format(runid)
            run(['docker', 'cp', str(saved_metadata), '{}:{}'.format(node, metadata_container)])
            print('Metadata:', saved_metadata, '\nSHA256:', record['metadata_sha256'], flush=True)
        cli_args=['conway','transaction','build']
        for ref in selected: cli_args += ['--tx-in',ref]
        cli_args += ['--tx-out','{}+{}'.format(dst,love),'--change-address',src]
        if metadata_container:
            cli_args += ['--metadata-json-file', metadata_container]
        cli_args += ['--out-file','/tmp/{}.body'.format(runid)]
        print('Node:',node,'\nAmount:',args.amount,'ADA\nInputs:',selected,flush=True)
        out = remote(node,*cli_args,timeout=90)
        print('Build:',out,flush=True)
        found = re.search(r'Estimated transaction fee:\s*(\d+)',out)
        if found: record['fee_lovelace_estimated']=found.group(1)
        run(['docker','cp','{}:/tmp/{}.body'.format(node,runid),str(folder/'tx.body')])
        if not args.execute:
            record['status']='DRY_RUN_BUILT'; print('DRY RUN: unsigned body created; nothing signed or submitted.')
            return 0
        run([args.cli,'conway','transaction','sign','--tx-body-file',folder/'tx.body',
             '--signing-key-file',key,'--testnet-magic',str(args.network_magic),
             '--out-file',folder/'tx.signed'])
        txhash=parse_txhash(run([args.cli,'conway','transaction','txid','--tx-file',folder/'tx.signed']))
        record['txhash']=txhash
        run(['docker','cp',str(folder/'tx.signed'),'{}:/tmp/{}.signed'.format(node,runid)])
        t0=time.monotonic()
        out=remote(node,'conway','transaction','submit','--tx-file','/tmp/{}.signed'.format(runid),timeout=60)
        record['submit_seconds']=round(time.monotonic()-t0,4)
        print('Submitted:',out,'\nTX HASH:',txhash,flush=True)
        record['status']='SUBMITTED_UNCONFIRMED'
        (folder/'submission.txt').write_text(out+'\n')
        # Check transaction-produced outputs by their hash and receiving address.
        # A UTxO present on-chain is stronger evidence than empty mempool.
        confirmed={}
        while time.monotonic()-t0 < args.timeout:
            for peer in peers:
                if peer in confirmed: continue
                try:
                    # Query recipient UTxOs; output index is not assumed.
                    outputs = utxos(peer, dst)
                    if any(ref.startswith(txhash + '#') and
                           int(v.get('value',{}).get('lovelace',0)) >= love
                           for ref,v in outputs.items()):
                        confirmed[peer]=round(time.monotonic()-t0,4)
                        print('Confirmed at',peer,'after',confirmed[peer],'seconds',flush=True)
                except (Failure, ValueError):
                    pass # a lagging node can be temporarily inaccessible
            if len(confirmed)==len(peers): break
            time.sleep(args.interval)
        record['confirmed_nodes'] = dict(sorted(confirmed.items()))
        record['confirmation_seconds']=confirmed.get(node,'')
        record['status']='CONFIRMED_ALL' if len(confirmed)==len(peers) else ('CONFIRMED_PARTIAL' if confirmed else 'SUBMITTED_UNCONFIRMED_TIMEOUT')
        print('Final status:',record['status'],flush=True)
        return 0 if confirmed else 2
    except (Failure,ValueError,KeyError,json.JSONDecodeError) as e:
        record['error']=str(e);record['status']='ERROR' if record['status']=='started' else record['status']
        print('ERROR:',e,file=sys.stderr)
        return 1
    finally:
        record['utc_finished']=dt.datetime.now(dt.timezone.utc).isoformat()
        (folder/'result.json').write_text(json.dumps(record,indent=2)+'\n')
        save_record(csv_file,record)
        print('Recorded:',folder/'result.json','and',csv_file,flush=True)

if __name__=='__main__': sys.exit(main())
