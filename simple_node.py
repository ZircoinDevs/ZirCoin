from zircoin.api import Node
from zircoin.wallet import Wallet

import argparse

# args
parser = argparse.ArgumentParser(
    description='ZirCoin command line node')
parser.add_argument("--wallet", "-w", type=str, help="Path to wallet file")
args = parser.parse_args()

# modules

wallet = Wallet(file=(args.wallet if args.wallet else "wallet.json"))
node = Node()


while True:
    opt = input("(NODE) > ")

    if opt == "exit":
        exit()

    if opt == "connection-pool":
        print(node.connection_pool.pool)

    if opt == "sync-status":
        print(node.consensus.sync_status)

    if opt == "block-height":
        print(node.blockchain.height)