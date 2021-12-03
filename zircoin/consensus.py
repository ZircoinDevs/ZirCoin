import json

import requests

from .blockchain import Blockchain
from .logger import Logger


class Consensus:

    def __init__(self, blockchain, connection_pool, protocol):
        self.blockchain = blockchain
        self.connection_pool = connection_pool
        self.protocol = protocol
        self.logger = Logger("consensus")

        self.sync_status = {
            "syncing": False,
            "progress": [0, 0],
            "download_node": None
        }

    @staticmethod
    def get_json(peer, url):
        try:
            response = requests.get(peer + url, timeout=2)
            return response.json()
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ConnectTimeout,
                requests.exceptions.ReadTimeout,
                requests.exceptions.HTTPError,
                json.decoder.JSONDecodeError):
            return None

    def consensus(self):
        while True:
            for peer in self.connection_pool.get_alive_peers(20):
                invalid_chain = False

                # get the peer information
                peer_info = self.get_json(peer, "/info")
                if not peer_info:
                    continue

                peer_block_height = peer_info["block_height"]

                if peer_block_height > self.blockchain.height:

                    is_sync = (peer_block_height - self.blockchain.height) > 2

                    if is_sync:
                        self.sync_status["syncing"] = True
                        self.sync_status["download_node"] = peer
                        self.sync_status["progress"][1] = peer_block_height

                    # get a list of the peer's block hashes
                    blockinv = self.get_json(peer, "/blockinv")

                    # if the peer is unreachable, move on
                    if not blockinv:
                        self.logger.error("Failed to get peer blockinv")
                        continue

                    for blockhash in blockinv:

                        # if the blockchain already contains the hash, move on
                        if self.blockchain.contains_hash(blockhash):
                            continue

                        block = self.get_json(peer, "/block/" + str(blockhash))

                        # if the block does not exist, set the chain as invalid and break
                        if not block:
                            self.logger.error(
                                "Could not get block from peer: " + str(blockhash))
                            invalid_chain = True
                            break

                        # if the block is invalid, set the chain as invalid and break
                        if not self.blockchain.add(block):
                            break

                        if is_sync:
                            self.sync_status["progress"][0] = block["height"]

                    # if the blockchain has been marked as invalid, move on
                    if invalid_chain:
                        print("invalid chain")
                        continue

                    # if no hashes match, create a new empty blockchain and sync to that
                    if not peer_block_height == self.blockchain.height:
                        new_blockchain = Blockchain(
                            self.blockchain.blockchain_id, create_genesis_block=False)
                        print("NEW BLOCKCHAIN")

                        for blockhash in blockinv:
                            block = self.get_json(peer, f"/block/{blockhash}")
                            if not block:
                                break

                            self.sync_status["progress"][0] = block["height"]

                            # add the block
                            if not new_blockchain.add(block, verbose=True):
                                self.logger.info(f"Invalid block: {blockhash}")
                                break

                        if new_blockchain.height > self.blockchain.height:
                            self.blockchain.clear()
                            for block in new_blockchain.chain:
                                if not self.blockchain.add(block, verbose=True):
                                    self.blockchain.clear(
                                        create_genesis_block=True)
                                    self.logger.info(
                                        "Cleared blockchain due to fraudulent blocks.")
                                    break

                        print("NEW BLOCKCHAIN")

            self.sync_status["syncing"] = False
            self.sync_status["download_node"] = None
            self.sync_status["progress"] = [0, 0]

    def transaction_consensus(self):
        while True:
            for peer in self.connection_pool.get_alive_peers(20):
                latest_block = self.get_json(peer, "/latest-block")
                if not latest_block:
                    continue

                # if the node is using a different blockchain, don't request transactions
                if latest_block["hash"] != self.blockchain.last_block["hash"]:
                    continue

                pending_transactions = self.get_json(
                    peer, "/pending-transactions")
                if not pending_transactions:
                    continue

                for transaction in pending_transactions:
                    self.blockchain.transaction_pool.add(transaction)
