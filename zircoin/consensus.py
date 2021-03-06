import json, simplejson
import requests
from threading import Thread
from time import time

from .blockchain import Blockchain
from .logger import Logger


class Consensus:

    def __init__(self, blockchain, connection_pool):
        self.blockchain = blockchain
        self.connection_pool = connection_pool
        self.logger = Logger("consensus")

        self.block_batch_size = 50

        self.sync_status = {
            "syncing": False,
            "progress": [0, 0],
            "download_node": None,
            "process": None,
            "speed": 0
        }

    @staticmethod
    def get_json(node, url):
        try:
            response = requests.get(node + url, timeout=2)
            return response.json()
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
                requests.exceptions.ConnectTimeout,
                requests.exceptions.ReadTimeout,
                requests.exceptions.HTTPError,
                json.decoder.JSONDecodeError,
                simplejson.errors.JSONDecodeError):
            return None

    def get_block(self, node, blockhash):
        for i in range(1, 3):
            block = self.get_json(node, f"/block/{blockhash}")
            if block:
                break

        return block

    def download_block_threaded(self, node, blockhash, return_list, block_number):
        block = self.get_block(node, blockhash)
        if not block:
            return False

        return_list[block_number] = block
        return True

    def sync_blockchain(self, blockchain, blockinv, node):
        blockchain.autosave = False

        # set to sync mode
        node_block_height = len(blockinv) - 1

        self.sync_status["syncing"] = True
        self.sync_status["download_node"] = node
        self.sync_status["progress"][1] = node_block_height
        self.sync_status["process"] = "batching block inventory"

        invalid_chain = False

        if blockchain.last_block and blockchain.last_block["hash"] in blockinv:
            blockinv = blockinv[blockchain.height:-1]

        # split blockinv into batches
        blockinv_batches = self.in_batches(blockinv, self.block_batch_size)

        for i, batch in enumerate(blockinv_batches):

            blockhashes = []
            for blockhash in batch:
                if not self.blockchain.contains_hash(blockhash):
                    blockhashes.append(blockhash)

            if len(blockhashes) == 0:
                continue

            blocks = [None] * len(blockhashes)
            threads = []

            start_time = time()

            self.sync_status["process"] = "downloading blocks"

            for j, blockhash in enumerate(blockhashes):
                thread = Thread(target=self.download_block_threaded,
                                args=(node, blockhash, blocks, j))
                thread.start()
                threads.append(thread)

            for thread in threads:
                thread.join()

            end_time = time()
            self.sync_status["speed"] = round(((end_time - start_time) / self.block_batch_size) * 100, 2)

            for block in blocks:
                if not block:
                    return blockchain

                self.sync_status["progress"][0] = block["height"] + 1

                if not blockchain.add(block, verbose=True):
                    return blockchain

            if i % 10 == 1:
                blockchain.save()

            self.sync_status["syncing"] = True
            self.sync_status["download_node"] = node
            self.sync_status["progress"][1] = node_block_height

        self.sync_status["syncing"] = False
        self.sync_status["download_node"] = None
        self.sync_status["progress"] = [0, 0]
        self.sync_status["process"] = None
        self.sync_status["speed"] = 0

        blockchain.autosave = True
        return blockchain

    def in_batches(self, items, size):
        batches = []
        current_batch = []
        for i, item in enumerate(items):
            current_batch.append(item)
            if (i+1) % size == 0 or i+1 == len(items):
                batches.append(current_batch)
                current_batch = []

        return batches

    def download_missing_blocks(self, node, blockinv):
        self.blockchain = self.sync_blockchain(self.blockchain, blockinv, node)

    def download_new_blockchain(self, node, blockinv):
        new_blockchain = Blockchain(
            self.blockchain.BLOCKCHAIN_ID, create_genesis_block=False, autosave=False)

        new_blockchain = self.sync_blockchain(new_blockchain, blockinv, node)

        if not new_blockchain or not new_blockchain.height:
            return False

        if new_blockchain.height > self.blockchain.height:
            self.blockchain.clear(autosave=False)
            self.sync_status["process"] = "adding blocks to blockchain"

            for block in new_blockchain.chain:
                if not self.blockchain.add(block, verbose=True):
                    self.blockchain.clear(
                        create_genesis_block=True)
                    self.logger.info(
                        "Cleared blockchain due to fraudulent blocks.")
                    return False

                if block["height"] % 1000 == 1:
                    self.blockchain.save()

        self.blockchain.autosave = True
        return True

    def download_latest_block(self, node):
        block = self.get_json(node, "/latest-block")
        if not block:
            return False

        if not self.blockchain.add(block):
            return False

    def get_longest_chain_node(self):
        best_node = None
        best_block_height = 0

        for node in self.connection_pool.get_alive_peers(20):
            # get the  node information
            node_info = self.get_json(node, "/info")
            if not node_info:
                continue

            if node_info["block_height"] > best_block_height:
                best_node = node
                best_block_height = node_info["block_height"]
        
        return best_node, (best_block_height if best_block_height > 0 else None)

    def consensus(self):
        while True:
            node, node_block_height = self.get_longest_chain_node()

            if not node or not node_block_height:
                continue

            height_difference = node_block_height - self.blockchain.height
            if height_difference == 1:
                if self.download_latest_block(node):
                    continue

            self.sync_status["process"] = "downloading block inventory"

            # get a list of the  node's block hashes
            blockinv = self.get_json(node, "/blockinv")

            # if the  node is unreachable, move on
            if not blockinv:
                continue

            if len(blockinv) < node_block_height:
                continue

            if blockinv[0] == self.blockchain.chain[0]["hash"] and self.blockchain.last_block["hash"] in blockinv:
                # if there are new blocks to download, sync to the existing blockchain
                self.download_missing_blocks(node, blockinv)
            else:
                # if the node's blockchain is new, sync to a new blockchain
                self.download_new_blockchain(node, blockinv)

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
