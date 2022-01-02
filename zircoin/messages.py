import requests
import json

connection_errors = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.ConnectTimeout,
    requests.exceptions.ReadTimeout,
    requests.exceptions.HTTPError
)

def broadcast_block(block, connection_pool, blockchain):
    if blockchain.last_block:
        peers = connection_pool.get_peers_with_blockhash(
            blockchain.chain[-1]["hash"], 20)
    else:
        peers = connection_pool.get_alive_peers(20)

    for peer in peers:
        try:
            requests.post(peer + "/block-recv", json.dumps(block))
        except connection_errors:
            continue

def broadcast_transaction(transaction, connection_pool):
    peers = connection_pool.get_alive_peers(20)

    for peer in peers:
        try:
            requests.post(peer + "/tx-recv", json.dumps(transaction))
        except connection_errors:
            continue