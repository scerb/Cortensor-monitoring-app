import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
from datetime import datetime
import threading
from web3 import Web3

notified_miners = set()
auto_update_job = None
sort_by_percentage = False
countdown_seconds = 0
eth_balances = {}

# Connect to Arbitrum Sepolia testnet
web3 = Web3(Web3.HTTPProvider("https://sepolia-rollup.arbitrum.io/rpc"))

if not web3.is_connected():
    print("Failed to connect to Arbitrum Sepolia RPC")
else:
    print("Connected to Arbitrum Sepolia RPC")

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

def fetch_all_miner_data():
    url = "https://lb-be-4.cortensor.network/leaderboard"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print("Fetch error:", e)
    return []

def convert_last_active(timestamp):
    if not timestamp:
        return "Unknown"
    now = datetime.now()
    last_time = datetime.fromtimestamp(timestamp)
    delta = now - last_time
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds} sec ago"
    elif seconds < 3600:
        return f"{seconds // 60} min {seconds % 60} sec ago"
    elif seconds < 86400:
        return f"{seconds // 3600} hr {(seconds % 3600) // 60} min ago"
    else:
        return f"{seconds // 86400} days ago"

def load_miner():
    try:
        with open("miners.json", "r") as file:
            return json.load(file)
    except:
        return []

def save_miner(new_miner_id):
    try:
        miners = load_miner()
        if new_miner_id not in miners:
            miners.append(new_miner_id)
            with open("miners.json", "w") as file:
                json.dump(miners, file, indent=4)
            return True
    except Exception as e:
        print("Error saving miner:", e)
    return False

def is_valid_eth_address(address):
    return (
        isinstance(address, str)
        and address.startswith("0x")
        and len(address) == 42
        and web3.is_address(address)
    )

def fetch_balances():
    global eth_balances
    leaderboard = fetch_all_miner_data()
    miners = load_miner()
    eth_balances.clear()

    miner_ids = [m["miner"] for m in leaderboard if m["miner"] in miners]

    def get_balance(miner_id):
        try:
            if not is_valid_eth_address(miner_id):
                print(f"Skipping invalid address: {miner_id}")
                return
            balance_wei = web3.eth.get_balance(miner_id)
            balance_eth = web3.from_wei(balance_wei, 'ether')
            eth_balances[miner_id] = round(balance_eth, 4)
        except Exception as e:
            print(f"Error fetching balance for {miner_id}: {e}")

    threads = []
    for miner_id in miner_ids:
        t = threading.Thread(target=get_balance, args=(miner_id,))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    update_table()

def update_table():
    global notified_miners
    leaderboard = fetch_all_miner_data()
    miners = load_miner()
    tree.delete(*tree.get_children())

    now = datetime.now()

    if sort_by_percentage:
        leaderboard = sorted(leaderboard, key=lambda x: (x.get("precommitPoint", 0) / max(x.get("precommitCounter", 1), 1)), reverse=True)
    else:
        leaderboard = sorted(leaderboard, key=lambda x: x.get("precommitCounter", 0), reverse=True)

    for miner in leaderboard:
        if miner.get("miner") in miners:
            def pct(point, count):
                return (point / count * 100) if count else 0

            last_active_ts = miner.get("last_active")
            last_active_str = convert_last_active(last_active_ts)

            inactive_sec = (now - datetime.fromtimestamp(last_active_ts)).total_seconds() if last_active_ts else 0

            precommit_pct = pct(miner.get('precommitPoint', 0), miner.get('precommitCounter', 1))

            full_id = miner.get("miner", "N/A")
            display_id = full_id[:5] + "..." + full_id[-5:] if len(full_id) > 10 else full_id

            values = (
                display_id,
                miner.get("ping_counter", "N/A"),
                f"{miner.get('precommitPoint', 0)}/{miner.get('precommitCounter', 1)}",
                f"{precommit_pct:.2f}%",
                f"{miner.get('commitPoint', 0)}/{miner.get('commitCounter', 1)}",
                f"{pct(miner.get('commitPoint', 0), miner.get('commitCounter', 1)):.2f}%",
                f"{miner.get('preparePoint', 0)}/{miner.get('prepareCounter', 1)}",
                f"{pct(miner.get('preparePoint', 0), miner.get('prepareCounter', 1)):.2f}%",
                f"{miner.get('createPoint', 0)}/{miner.get('createCounter', 1)}",
                f"{pct(miner.get('createPoint', 0), miner.get('createCounter', 1)):.2f}%",
                last_active_str,
                f"{eth_balances.get(full_id, 'N/A')} ETH"
            )

            item_id = tree.insert("", "end", values=values)

            if inactive_sec > 480:
                tree.item(item_id, tags=("inactive",))

            ToolTip(tree, full_id)

    tree.tag_configure("inactive", background="lightcoral")
    tree.config(height=len(tree.get_children()))

def auto_update():
    global auto_update_job, countdown_seconds
    update_table()
    countdown_seconds = int(refresh_interval.get()) * 60
    auto_update_job = root.after(60000, auto_update)

def update_countdown():
    global countdown_seconds
    if countdown_seconds > 0:
        mins, secs = divmod(countdown_seconds, 60)
        countdown_label.config(text=f"Next refresh in: {mins:02d}:{secs:02d}")
        countdown_seconds -= 1
    else:
        countdown_label.config(text="Refreshing...")
        update_table()
        countdown_seconds = int(refresh_interval.get()) * 60
    root.after(1000, update_countdown)

def toggle_sort_by_percentage():
    global sort_by_percentage
    sort_by_percentage = not sort_by_percentage
    update_table()

def save_interval():
    global countdown_seconds
    countdown_seconds = int(refresh_interval.get()) * 60
    print(f"Interval set to {refresh_interval.get()} minutes.")

def add_miner():
    miner_id = miner_id_entry.get().strip()
    if miner_id:
        if save_miner(miner_id):
            messagebox.showinfo("Success", f"Miner {miner_id} added.")
        else:
            messagebox.showwarning("Notice", f"Miner {miner_id} already exists or couldn't be saved.")
        miner_id_entry.delete(0, tk.END)
        update_table()

def remove_miner():
    miner_id = miner_id_entry.get().strip()
    if miner_id:
        miners = load_miner()
        if miner_id in miners:
            miners.remove(miner_id)
            with open("miners.json", "w") as file:
                json.dump(miners, file, indent=4)
            messagebox.showinfo("Success", f"Miner {miner_id} removed.")
            update_table()
        else:
            messagebox.showwarning("Not Found", f"Miner {miner_id} not found.")
        miner_id_entry.delete(0, tk.END)

root = tk.Tk()
root.title("Cortensor Miner Dashboard")

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

dash_tab = ttk.Frame(notebook)
notebook.add(dash_tab, text="Dashboard")

frame = tk.Frame(dash_tab)
frame.pack(padx=10, pady=10)

cols = ("Miner", "Ping", "Precommit", "Precommit %", "Commit", "Commit %", "Prepare", "Prepare %", "Create", "Create %", "Last Active", "Eth Balance")

tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)
for col in cols:
    tree.heading(col, text=col)
    if col == "Miner":
        tree.column(col, width=90, anchor="w")
    elif col == "Last Active" or col == "Eth Balance":
        tree.column(col, width=150, anchor="center")
    else:
        tree.column(col, width=80, anchor="center")
tree.pack(side="left")

scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)
scrollbar.pack(side="right", fill="y")

tk.Button(dash_tab, text="Refresh Now", command=update_table).pack(pady=5)
tk.Button(dash_tab, text="Refresh Balances", command=fetch_balances).pack(pady=5)

sort_button = tk.Button(dash_tab, text="Sort by Precommit %", command=toggle_sort_by_percentage)
sort_button.pack(pady=5)

countdown_label = tk.Label(dash_tab, text="")
countdown_label.pack()

add_tab = ttk.Frame(notebook)
notebook.add(add_tab, text="Add Miner")

miner_frame = tk.Frame(add_tab)
tk.Label(miner_frame, text="Add Miner ID").pack()
miner_id_entry = tk.Entry(miner_frame, width=20)
miner_id_entry.pack()
tk.Button(miner_frame, text="Add Miner", command=add_miner).pack()
tk.Button(miner_frame, text="Remove Miner", command=remove_miner).pack(pady=(5, 0))
miner_frame.pack(padx=10, pady=10)

settings_tab = ttk.Frame(notebook)
notebook.add(settings_tab, text="Settings")

options_frame = tk.Frame(settings_tab)
options_frame.pack(pady=10)

auto_frame = tk.Frame(options_frame)
tk.Label(auto_frame, text="Auto Refresh Interval (min)").pack()
refresh_interval = tk.Entry(auto_frame, width=5)
refresh_interval.insert(0, "10")
refresh_interval.pack()
tk.Button(auto_frame, text="Save Interval", command=save_interval).pack(pady=5)
auto_frame.pack(side="left", padx=10)

update_table()
countdown_seconds = int(refresh_interval.get()) * 60
update_countdown()
auto_update()

root.mainloop()
