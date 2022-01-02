from zircoin.api import Client
from zircoin.wallet import Wallet

import argparse

# args
parser = argparse.ArgumentParser(
    description='ZirCoin command line miner')
parser.add_argument("--wallet", "-w", type=str, help="Path to wallet file")
args = parser.parse_args()

# modules

wallet = Wallet(file=(args.wallet if args.wallet else "wallet.json"))
client = Client()

client.miner.mine(wallet)

