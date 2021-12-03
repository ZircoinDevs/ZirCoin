import json
from time import time

from hashlib import sha256
from nacl.encoding import HexEncoder
from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey


class TransactionPool:
    def __init__(self, blockchain):
        self.pool = []
        self.unconfirmed_pool = []
        self.blockchain = blockchain

    @property
    def txids(self):
        ids = []
        for transaction in self.pool:
            ids.append(transaction["id"])

        return ids

    @property
    def unconfirmed_txids(self):
        ids = []
        for transaction in self.unconfirmed_pool:
            ids.append(transaction["id"])

        return ids

    def add(self, transaction):
        if not self.validate_transaction(transaction):
            return False

        if transaction["id"] in self.txids or transaction["id"] in self.unconfirmed_txids:
            return False

        if not self.check_for_overspending(transaction):
            return False

        self.pool.append(transaction)
        return True

    def create_transaction(self, private_key, public_key, receiver, amount):
        transaction = {
            "type": "payment",
            "sender": public_key,
            "receiver": receiver,
            "amount": amount,
            "timestamp": int(time()),
        }

        transaction_bytes = json.dumps(transaction, sort_keys=True).encode("ascii")
        transaction["id"] = sha256(transaction_bytes).hexdigest()

        signing_key = SigningKey(private_key, encoder=HexEncoder)

        signature = signing_key.sign(transaction_bytes).signature
        transaction["signature"] = HexEncoder.encode(signature).decode("ascii")

        return transaction

    @staticmethod
    def create_coinbase_transaction(receiver, amount):
        transaction = {
            "type": "coinbase",
            "sender": "coinbase",
            "receiver": receiver,
            "amount": amount,
            "timestamp": int(time()),
        }

        transaction_bytes = json.dumps(transaction, sort_keys=True).encode("ascii")
        transaction["id"] = sha256(transaction_bytes).hexdigest()

        return transaction

    def validate_transaction(self, full_transaction):

        if full_transaction["amount"] > self.blockchain.get_balance(full_transaction["sender"]):
            return False

        transaction = full_transaction.copy()
        public_key = transaction["sender"]
        txid = transaction.pop("id")
        signature = transaction.pop("signature")

        # verify signature
        signature = HexEncoder.decode(signature)
        transaction = json.dumps(transaction, sort_keys=True).encode("ascii")
        verify_key = VerifyKey(public_key, encoder=HexEncoder)

        # verify txid
        if sha256(transaction).hexdigest() != txid:
            return False

        try:
            verify_key.verify(transaction, signature)
        except BadSignatureError:
            return False

        return True

    def get_balance_from_pool(self, public_key):
        """
        Gets the balance of a wallet from transactions in the transaction pool

        :param str public_key: The public key of the wallet to check the balance of
        :return float balance: The counted balance of the wallet
        """
        balance = 0.0

        for transaction in self.pool:
            if transaction["sender"] == public_key:
                balance -= transaction["amount"]
            if transaction["receiver"] == public_key:
                balance += transaction["amount"]

        return balance

    def check_for_overspending(self, transaction):
        """
        Checks for overspent transactions that create a negative balance

        :param dict transaction: The transaction to be checked
        :return bool result: True if there is no overspending, else false
        """
        # find the balance of the sender in the current blockchain and tx pool, then minus the transaction amount
        balance = self.blockchain.get_balance(transaction["sender"]) + self.get_balance_from_pool(transaction["sender"])
        balance -= transaction["amount"]

        # if the balance is below zero, the transaction is overspent
        if balance < 0:
            return False
        else:
            return True

    def get_pending_transactions(self, transaction_inv):
        pending_transactions = []
        for transaction in self.pool:
            if not transaction["id"] in transaction_inv:
                pending_transactions.append(transaction)

        return pending_transactions

    def update_pool(self, blockchain):
        for transaction in blockchain[-1]["transactions"]:
            if transaction in self.pool:
                self.pool.remove(transaction)
                self.unconfirmed_pool.append(transaction)

        if len(blockchain) < 5:
            return True

        for transaction in self.unconfirmed_pool:
            if transaction in blockchain[-5]["transactions"]:
                self.unconfirmed_pool.remove(transaction)
