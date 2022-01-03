from tkinter import *
from tkinter import messagebox
from tkinter.ttk import Progressbar
from threading import Thread
from time import time
import webbrowser
import string

from zircoin.api import Client
from zircoin.wallet import Wallet
from zircoin.messages import broadcast_transaction

client = Client()
wallet = Wallet()

root = Tk()
root.geometry("700x400")
root.title("ZirCoin Wallet")
root.resizable(False, False)

def get_balance():
    bal = client.blockchain.get_balance(wallet.public_key)
    label_text = f"Balance: {'{:,}'.format(bal)} ZIR"
    balance.config(text=str(label_text))
    balance.after(100, get_balance)

def update_sync_progressbar():
    sync_status = client.consensus.sync_status["progress"]

    if 0 in sync_status:
        sync_progress["value"] = 0
        root.update_idletasks()
        sync_progress.after(100, update_sync_progressbar)
        return

    progress_out_of_700 = int((sync_status[0] / sync_status[1]) * 700)

    sync_progress["value"] = progress_out_of_700

    root.update_idletasks()
    sync_progress.after(100, update_sync_progressbar)

def update_sync_label():
    if not client.consensus.sync_status["syncing"]:
        sync_label.config(text="Up to date")
    else:
        sync_label.config(text="Syncing blockchain...")
    
    root.update_idletasks()
    sync_label.after(20, update_sync_label)


def popup():
    win = Toplevel()
    win.wm_title("Window")

    t = Text(win, height=5)
    t.insert(INSERT, wallet.public_key)
    t.pack()

    b = Button(win, text="Okay", command=win.destroy)
    b.pack()


def transfer():
    amount = amount_var.get()
    receiver = receiver_var.get()

    try:
        amount = float(amount)
    except ValueError:
        messagebox.showinfo("Error", "Invalid amount.")
        return False

    if amount > client.blockchain.get_balance(wallet.public_key):
        messagebox.showinfo("Error", "Not enough balance.")
        return False

    if len(receiver) != 64:
        messagebox.showinfo("Error", "Invalid receiver.")
        return False

    for char in receiver:
        if char not in string.ascii_lowercase + string.hexdigits:
            messagebox.showinfo("Error", "Invalid receiver.")
            return False

    transaction = client.blockchain.transaction_pool.create_transaction(
        wallet.private_key,
        wallet.public_key,
        receiver,
        amount
    )

    if client.blockchain.transaction_pool.add(transaction):
        broadcast_transaction(transaction, client.connection_pool)
        amount_var.set("")
        receiver_var.set("")
    else:
        messagebox.showinfo("Error", "The transaction could not be added.")


menubar = Menu(root)

filemenu = Menu(menubar, tearoff=0)
filemenu.add_command(label="Exit", command=root.quit)
menubar.add_cascade(label="File", menu=filemenu)

walletmenu = Menu(menubar, tearoff=0)
walletmenu.add_command(label="Receiving address", command=popup)
menubar.add_cascade(label="Wallet", menu=walletmenu)

helpmenu = Menu(menubar, tearoff=0)
helpmenu.add_command(label="Website", command=lambda: webbrowser.open("zircoin.network"))
helpmenu.add_command(label="Github", command=lambda: webbrowser.open("github.com/zircoindevs/zircoin"))
menubar.add_cascade(label="Help", menu=helpmenu)


title = Label(text="ZirCoin Wallet", font=("", 27))
title.grid(pady=(5, 35), padx=(5, 5), sticky=W)

balance = Label(font=("", 16))
balance.grid(padx=(5, 5), sticky=W)
get_balance()

sync_label = Label()
sync_label.place(relx=0.0, rely=0.95, anchor="sw")
update_sync_label()

sync_progress = Progressbar(orient=HORIZONTAL,length=700, mode="determinate")
sync_progress["maximum"] = 700
sync_progress.place(relx=0, rely=1.0, anchor="sw")
update_sync_progressbar()


transfer_label = Label(text="Transfer", font=("", 18))
transfer_label.grid(sticky=W, padx=5, pady=(50, 20))



transfer_entry_receiver_label = Label(text="Receiver")
transfer_entry_receiver_label.grid(row=5, column=0, sticky=W, padx=(5, 0))

receiver_var = StringVar()
transfer_entry_receiver = Entry(textvariable=receiver_var)
transfer_entry_receiver.grid(row=5, padx=(30, 0))


transfer_entry_amount_label = Label(text="Amount")
transfer_entry_amount_label.grid(row=6, column=0, sticky=W, padx=(5, 0))

amount_var = StringVar()
transfer_entry_amount = Entry(textvariable=amount_var)
transfer_entry_amount.grid(row=6, padx=(30, 0))

transfer_button = Button(text="Transfer", command=transfer)
transfer_button.grid(padx=5, pady=5, sticky=W)

root.config(menu=menubar)
root.mainloop()