from .logger import Logger
import sys

logger = Logger("Graphs")

try:
    import matplotlib.pyplot as plt
except ImportError:
    pass


def wealth_distrobution(blockchain):
    if "matplotlib" not in sys.modules:
        logger.info(
            "Please install the matplotlib python package to use this feature.")
        return False

    wallets = {}
    keys = []

    for block in blockchain.chain:
        for transaction in block["transactions"]:
            wallets[transaction["receiver"]] = 0

    for wallet in wallets:
        bal = blockchain.get_balance(wallet)
        if bal > 0:
            wallets[wallet] = bal

        keys.append(f"{wallet[0:3]}...{wallet[-3:]}")

    fig1, ax1 = plt.subplots()
    ax1.pie(wallets.values(), labels=keys, autopct='%1.1f%%',
            shadow=True, startangle=90)
    ax1.axis('equal')
    plt.title("Wealth distrobution", fontdict={
              'family': 'sans-serif', 'color': 'black', 'size': 20}, pad=15)
    plt.show()
