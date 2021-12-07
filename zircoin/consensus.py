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
    def get_json(node, url):
        try:
            response = requests.get(node + url)
            return response.json()
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ConnectTimeout,
                requests.exceptions.ReadTimeout,
                requests.exceptions.HTTPError,
                json.decoder.JSONDecodeError):
            return None

    def get_block(self, node, blockhash):
        for i in range(1, 3):
            block = self.get_json(node, f"/block/{blockhash}")
            if block:
                break

        return block

    def download_missing_blocks(self, node, blockinv):
        # set to sync mode
        node_block_height = len(blockinv) - 1

        is_sync = node_block_height - self.blockchain.height > 2
        if is_sync:
            self.sync_status["syncing"] = True
            self.sync_status["download_node"] = node
            self.sync_status["progress"][1] = node_block_height

        invalid_chain = False

        # download and add blocks
        for blockhash in blockinv:

            # if the blockchain already contains the hash, move on
            if self.blockchain.contains_hash(blockhash):
                continue

            block = self.get_json(node, "/block/" + str(blockhash))

            # if the block can't be retrieved, set it as invalid and break
            if not block:
                self.logger.error(
                    "Could not get block from  node: " + str(blockhash))
                invalid_chain = True
                break

            # if the block is invalid, set the chain as invalid and break
            if not self.blockchain.add(block):
                break

            if is_sync:
                self.sync_status["progress"][0] = block["height"]

        if is_sync:
            self.sync_status["syncing"] = True
            self.sync_status["download_node"] = node
            self.sync_status["progress"][1] = node_block_height

        # if the blockchain has been marked as invalid, move on
        if invalid_chain:
            self.blockchain.clear(create_genesis_block=True)
            return False

        return True

    def download_new_blockchain(self, node, blockinv):
        self.sync_status["syncing"] = True
        self.sync_status["download_node"] = node
        self.sync_status["progress"][1] = len(blockinv)

        new_blockchain = Blockchain(
            self.blockchain.blockchain_id, create_genesis_block=False, autosave=False)

        for blockhash in blockinv:
            block = self.get_block(node, blockhash)
            if not block:
                self.logger.error(
                    "Could not get block from  node: " + str(blockhash))
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
                    return False
        return True

    def download_latest_block(self, node):
        block = self.get_json(node, "/latest-block")
        if not block:
            return False

        if not self.blockchain.add(block):
            return False

    def consensus(self):
        while True:
            for node in self.connection_pool.get_alive_peers(20):
                # get the  node information
                node_info = self.get_json(node, "/info")
                if not node_info:
                    continue

                node_block_height = node_info["block_height"]

                if node_block_height > self.blockchain.height:

                    if node_block_height - self.blockchain.height == 1:
                        if self.download_latest_block(node):
                            continue

                    # get a list of the  node's block hashes
                    blockinv = self.get_json(node, "/blockinv")

                    # if the  node is unreachable, move on
                    if not blockinv:
                        self.logger.error("Failed to get  node blockinv")
                        continue

                    if blockinv[0] == self.blockchain.chain[0]["hash"]:
                        # if there are new blocks to download, sync to the existing blockchain
                        self.download_missing_blocks(node, blockinv)
                    else:
                        # if the node's blockchain is new, sync to a new blockchain
                        self.download_new_blockchain(node, blockinv)

                    self.sync_status["syncing"] = False
                    self.sync_status["download_node"] = None
                    self.sync_status["progress"] = [0, 0]

    def transaction_consensus(self):
        while True:
            for node in self.connection_pool.get_alive_peers(20):
                latest_block = self.get_json(node, "/latest-block")
                if not latest_block:
                    continue

                # if the node is using a different blockchain, don't request transactions
                if latest_block["hash"] != self.blockchain.last_block["hash"]:
                    continue

                pending_transactions = self.get_json(
                    node, "/pending-transactions")
                if not pending_transactions:
                    continue

                for transaction in pending_transactions:
                    self.blockchain.transaction_pool.add(transaction)
