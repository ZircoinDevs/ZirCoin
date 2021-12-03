from zircoin.wallet import Wallet
from zircoin.miner import Miner
from zircoin.logger import Logger
from zircoin.server import Server
from zircoin.consensus import Consensus
from zircoin.protocol import Protocol
from zircoin.connections import ConnectionPool
from zircoin.blockchain import Blockchain

import heapq
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
blockchain = Blockchain(config["blockchain_id"])
blockchain.load()

# init modules

if args.wallet is None:
    wallet = Wallet()
else:
    wallet = Wallet(wallet_file=args.wallet)

connection_pool = ConnectionPool(
    config, NODE_ID, server_config["port"])
protocol = Protocol(blockchain, connection_pool,
                    server_config, config, NODE_ID)
server = Server(blockchain, protocol, server_config)

consensus = Consensus(blockchain, connection_pool, protocol)
miner = Miner(blockchain, protocol, wallet, config, consensus)

logger = Logger("zircoin")


def menu():
    run = True

    def mine():
        if not consensus.sync_status["syncing"]:
            miner.mine()
        else:
            logger.info("Cannot start mining: syncing is in progress.")

    def wallet_info():
        print(f"Wallet address: {wallet.public_key}")
        balance = blockchain.get_balance(wallet.public_key)
        print(f"Balance: {balance} ◈ ZIR")

    def get_wallet_balance():
        address = input("Wallet address: ")
        balance = blockchain.get_balance(address)
        print(f"Balance: {balance} ◈ ZIR")

    def network_stats():
        wallets = {}
        for block in blockchain.chain:
            for transaction in block["transactions"]:
                wallets[transaction["receiver"]] = 0

        for wallet in wallets:
            wallets[wallet] = blockchain.get_balance(wallet)

        richest_wallets = heapq.nlargest(5, wallets, key=wallets.get)

        print("Rich list: \n")
        for i, wallet in enumerate(richest_wallets):
            print(f"{str(i+1)} - {wallet} [{str(wallets[wallet])} ZIR]")

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

        transaction = blockchain.transaction_pool.create_transaction(
            wallet.private_key,
            wallet.public_key,
            receiver,
            amount
        )

        if blockchain.transaction_pool.add(transaction):
            logger.info("Transaction added.")
            if config["fullnode"] == False:
                protocol.broadcast_transaction(transaction)
        else:
            logger.info("Transaction invalid.")

    def display_blockchain():
        print(str(blockchain))

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
        print("Protocol version: " + protocol.version)
        print("Node ID: " + protocol.node_id)
        print("Block height: " + str(blockchain.height))

    def display_sync_status():
        if consensus.sync_status["syncing"]:
            print("Syncing...\n")
            progress = consensus.sync_status["progress"]
            print("Progress: " + str(progress[0]) + "/" + str(progress[1]))
            if consensus.sync_status["download_node"]:
                print("Downloading from node: " +
                      consensus.sync_status["download_node"])
        else:
            print("Up to date\n")

    options = {
        'w': {"handler": wallet_info, "name": "Wallet"},
        'b': {"handler": get_wallet_balance, "name": "Check balance"},
        'r': {"name": "Rich list", "handler": network_stats},
        'm': {"handler": mine, "name": "Mine"},
        't': {"handler": add_transaction, "name": "Transfer"},
        's': {"handler": display_sync_status, "name": "Sync status"},

        '1': {"handler": display_blockchain, "name": "Display blockchain"},
        '2': {"handler": display_connection_pool, "name": "Connection pool"},
        '3': {"handler": display_peer_info, "name": "Peer info"},
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
