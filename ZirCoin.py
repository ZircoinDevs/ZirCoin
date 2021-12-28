from zircoin.wallet import Wallet
from zircoin.miner import Miner
from zircoin.logger import Logger
from zircoin.server import Server
from zircoin.consensus import Consensus
from zircoin.networking import HttpRoutes
from zircoin.connections import ConnectionPool
from zircoin.blockchain import Blockchain
from zircoin.version import PROTOCOL_VERSION, NETWORKING_VERSION, SOFTWARE_VERSION
from zircoin.utils import test_hashrate
from zircoin.plotting import (
    wealth_distrobution,
    transaction_volume,
    transaction_quantity,
    coin_supply,
    difficulty,
    block_time
)

import heapq
import string
import argparse
import json
import time
import random
import hashlib
from threading import Thread
from colorama import Fore, Style, init
init()


# parse args
parser = argparse.ArgumentParser(
    description='Decentralised cryptocurrency blockchain')
parser.add_argument("--port", "-p", type=int, help="Port for server to run on")
parser.add_argument("--fullnode", "-f", default=False, action="store_true",
                    help="Eneble fullnode mode (must be port forwarded)")
parser.add_argument("--wallet", "-w", type=str, help="Path to wallet file")
parser.add_argument("--blockchain", "-b", type=str, help="Path to blockchain json file")
args = parser.parse_args()

# constants
NODE_ID = hashlib.sha256(str(random.getrandbits(256)).encode()).hexdigest()

# application config
config = json.load(open("config.json", "r"))

# overide fullnode if --fullnode or -f is used
if args.fullnode:
    config["fullnode"] = True

# server config

if config["multiport_mode"]:
    if args.port is not None:
        port = args.port
    else:
        port = 2227
else:
    port = 2227

server_config = {
    "ip": "0.0.0.0",
    "port": port
}

# init blockchain

if args.blockchain:
    blockchain = Blockchain(config["blockchain_id"], file=args.blockchain)
else:
    blockchain = Blockchain(config["blockchain_id"])
blockchain.load()

# init modules

if args.wallet is None:
    wallet = Wallet()
else:
    wallet = Wallet(wallet_file=args.wallet)

connection_pool = ConnectionPool(
    config, NODE_ID, server_config["port"])
http_routes = HttpRoutes(blockchain, connection_pool,
                    server_config, config, NODE_ID)
server = Server(blockchain, http_routes, server_config)

consensus = Consensus(blockchain, connection_pool, http_routes)
miner = Miner(blockchain, http_routes, wallet, config, consensus)

logger = Logger("zircoin")


def menu():
    run = True

    def mine():
        miner.mine()

    def wallet_info():
        print(f"Wallet address: {wallet.public_key}")
        balance = blockchain.get_balance(wallet.public_key)
        print(f"Balance: {balance} ◈ ZIR")

    def get_wallet_balance():
        address = input("Wallet address: ")
        balance = blockchain.get_balance(address)
        print(f"Balance: {balance} ◈ ZIR")

    def zircoin_stats():
        # richlist
        wallets = {}
        for block in blockchain.chain:
            for transaction in block["transactions"]:
                wallets[transaction["receiver"]] = 0

        for wallet in wallets:
            wallets[wallet] = blockchain.get_balance(wallet)

        richest_wallets = heapq.nlargest(10, wallets, key=wallets.get)

        print("Rich list: \n")
        for i, wallet in enumerate(richest_wallets):
            print(f"{str(i+1)} - {wallet} [{str(wallets[wallet])} ZIR]")

        # wallets
        print("\nWallet count: " + str(len(wallets)))

        # active miners

        blocks = blockchain.get_blocks_after_timestamp(time.time() - 60*20)
        miners = set()

        for block in blocks:
            miners.add(block["transactions"][0]["receiver"])

        print("\nActive miners: ")
        for miner in miners:
            print(miner)

        # circulating supply

        supply = 0

        for wallet, balance in wallets.items():
            supply += balance

        print("\nCoins in circulation: " + str(supply))

        # average block time

        start_time = blockchain.chain[0]["time"]
        end_time = blockchain.chain[-1]["time"]

        total_time = end_time - start_time
        block_time = total_time / blockchain.height

        print("\nAverage block time: " + str(round(block_time)) + "s")

        # time until halving

        next_halving = blockchain.height + (100000 - blockchain.height % 100000)
        blocks_until_halving = next_halving - blockchain.height
        estimated_time_seconds = block_time * blocks_until_halving
        estimated_time_days = estimated_time_seconds/60/60/24

        print(
            f"\nTime until next halving: {blocks_until_halving} blocks, aprox. {round(estimated_time_days)} days")

    def add_transaction():
        print("Create a transaction\n")
        receiver = input("Receiver: ")
        amount = input("Amount: ◈ ")

        try:
            amount = float(amount)
        except ValueError:
            if amount.lower() == "all":
                amount = blockchain.get_balance(wallet.public_key)
            else:
                print("Invalid amount")
                return False

        if amount > blockchain.get_balance(wallet.public_key):
            logger.info("Insufficient balance")
            return False

        if len(receiver) != 64:
            logger.info("Invalid receiver")
            return False

        for char in receiver:
            if char not in string.ascii_lowercase + string.hexdigits:
                logger.info("Invalid receiver")
                return False

        transaction = blockchain.transaction_pool.create_transaction(
            wallet.private_key,
            wallet.public_key,
            receiver,
            amount
        )

        if blockchain.transaction_pool.add(transaction):
            logger.info("Transaction added.")
            if config["fullnode"] == False:
                http_routes.broadcast_transaction(transaction)
        else:
            logger.info("Transaction invalid.")

    def transaction_history():
        transactions = []

        for block in blockchain.chain:
            for transaction in block["transactions"]:
                if transaction["sender"] == wallet.public_key or transaction["receiver"] == wallet.public_key:
                    transactions.append(transaction)

        print("\nTransaction History\n")
        for transaction in transactions:
            receiver = transaction["receiver"]
            sender = transaction["sender"]
            amount = transaction["amount"]

            if transaction["type"] == "coinbase":
                continue
            elif transaction["sender"] == wallet.public_key:
                print(f"{amount} {(10-len(str(amount)))*' '}| You --> {receiver}")
            else:
                print(f"{amount} {(10-len(str(amount)))*' '}| {sender} --> You")

    def display_blockchain():
        blocks = blockchain.chain[-11:-1]
        for block in blocks:
            print(blockchain.display_block(block))

    def display_connection_pool():
        active_peers = list(connection_pool.pool)
        inactive_peers = list(connection_pool.inactive_pool)
        print("Active:")
        for peer in active_peers:
            print(f"  - {peer}")
        print("none") if len(active_peers) == 0 else None

        print("\nInactive:")
        for peer in inactive_peers:
            print(f"  - {peer}")
        print("none") if len(inactive_peers) == 0 else None

    def display_peer_info():
        print("Blockchain protocol version: " + PROTOCOL_VERSION)
        print("HttpRoutes Version: " + NETWORKING_VERSION)
        print("Software Version: " + SOFTWARE_VERSION)

        print("\nNode ID: " + http_routes.NODE_ID)
        print("Block height: " + str(blockchain.height))

    def display_sync_status():
        if consensus.sync_status["syncing"]:
            print("Syncing...\n")
            progress = consensus.sync_status["progress"]
            percentage = progress[0] / progress[1] * 100

            if consensus.sync_status["process"]:
                print(f"Process: {consensus.sync_status['process']}")
            print(f"Progress: {progress[0]} / {progress[1]} ({round(percentage)}%)")
            if consensus.sync_status["download_node"]:
                print(f"Downloading from node: {consensus.sync_status['download_node']}")

            print(f"Download speed: {consensus.sync_status['speed']}s per 100 blocks")
        else:
            print("Up to date\n")

    def hashrate():
        print("Testing...")
        megahashes = test_hashrate() / 1000000
        print(f"Your hashrate: {round(megahashes, 2)} MH/s")

    def graphs():
        opt = input("""
ZirCoin Graphs

1) Wealth distrobution
2) Transaction Volume
3) Transaction quantity
4) Circulating supply
5) Mining difficulty
6) Block time

>> """)

        if opt == "1":
            wealth_distrobution(blockchain)
        elif opt == "2":
            transaction_volume(blockchain)
        elif opt == "3":
            transaction_quantity(blockchain)
        elif opt == "4":
            coin_supply(blockchain)
        elif opt == "5":
            difficulty(blockchain)
        elif opt == "6":
            block_time(blockchain)

    options = {
        'w': {"handler": wallet_info, "name": "Wallet"},
        'b': {"handler": get_wallet_balance, "name": "Check balance"},
        'e': {"name": "Economy stats", "handler": zircoin_stats},
        'm': {"handler": mine, "name": "Mine"},
        't': {"handler": add_transaction, "name": "Transfer"},
        'h': {"handler": transaction_history, "name": "Transaction history"},
        's': {"handler": display_sync_status, "name": "Sync status"},

        '1': {"handler": display_blockchain, "name": "Latest blocks"},
        '2': {"handler": display_connection_pool, "name": "Connection pool"},
        '3': {"handler": display_peer_info, "name": "Peer info"},
        '4': {"handler": hashrate, "name": "Test hashrate"},
        '5': {"handler": graphs, "name": "Graphs"},
    }

    banner = open("data/banner.txt", "r").read()
    print(Fore.CYAN + banner + "\nWelcome!\n" + Style.RESET_ALL)

    while run:
        for option in options:
            if option == '1':
                print("\n")

            print(Fore.CYAN + option + ") " + Style.RESET_ALL +
                  options[option]["name"])

        opt = input(">")
        if opt in options:
            print("\n")
            try:
                options[opt]["handler"]()
            except KeyboardInterrupt:
                pass
            print("\n")


def main():
    if config["fullnode"]:
        server_thread = Thread(target=server.start_server, args=(
            server.aiohttp_server(),), name="server")
        server_thread.daemon = True
        server_thread.start()

    connection_pool.add_seed_nodes()

    consensus_thread = Thread(target=consensus.consensus, name="consensus")
    consensus_thread.daemon = True
    consensus_thread.start()
    time.sleep(0.1)

    transaction_consensus_thread = Thread(
        target=consensus.transaction_consensus, name="txconsensus")
    transaction_consensus_thread.daemon = True
    transaction_consensus_thread.start()
    time.sleep(0.1)

    try:
        menu()
    except KeyboardInterrupt:
        print("\n")
        exit()


if __name__ == "__main__":
    main()
