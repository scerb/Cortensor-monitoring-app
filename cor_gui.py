import tkinter as tk
from tkinter import ttk
import requests
import json
from datetime import datetime

notified_miners = set()
auto_update_job = None
sort_by_percentage = False  # Flag to toggle sorting by precommit percentage
countdown_seconds = 0  # Countdown for next refresh

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

            if last_active_ts:
                inactive_sec = (now - datetime.fromtimestamp(last_active_ts)).total_seconds()
                if inactive_sec > 20:
                    if miner["miner"] not in notified_miners:
                        notified_miners.add(miner["miner"])
                else:
                    notified_miners.discard(miner["miner"])

            precommit_pct = pct(miner.get('precommitPoint', 0), miner.get('precommitCounter', 1))

            tree.insert("", "end", values=(
                miner.get("miner", "N/A"),
                miner.get("ping_counter", "N/A"),
                f"{miner.get('precommitPoint', 0)}/{miner.get('precommitCounter', 1)}",
                f"{precommit_pct:.2f}%",
                f"{miner.get('commitPoint', 0)}/{miner.get('commitCounter', 1)}",
                f"{pct(miner.get('commitPoint', 0), miner.get('commitCounter', 1)):.2f}%",
                f"{miner.get('preparePoint', 0)}/{miner.get('prepareCounter', 1)}",
                f"{pct(miner.get('preparePoint', 0), miner.get('prepareCounter', 1)):.2f}%",
                f"{miner.get('createPoint', 0)}/{miner.get('createCounter', 1)}",
                f"{pct(miner.get('createPoint', 0), miner.get('createCounter', 1)):.2f}%",
                last_active_str
            ))

    tree.config(height=len(tree.get_children()))

def auto_update():
    global auto_update_job, countdown_seconds
    if auto_var.get():
        update_table()
        countdown_seconds = int(refresh_interval.get()) * 60
        auto_update_job = root.after(60000, auto_update)
    else:
        if auto_update_job:
            root.after_cancel(auto_update_job)
        countdown_label.config(text="")

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

# GUI Setup
root = tk.Tk()
root.title("Cortensor Miner Dashboard")

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True)

# Dashboard Tab
dashboard_tab = ttk.Frame(notebook)
notebook.add(dashboard_tab, text="Dashboard")

frame = tk.Frame(dashboard_tab)
frame.pack(padx=10, pady=10)

cols = ("Miner", "Ping",
        "Precommit", "Precommit %",
        "Commit", "Commit %",
        "Prepare", "Prepare %",
        "Create", "Create %",
        "Last Active")

tree = ttk.Treeview(frame, columns=cols, show="headings", height=20)
for i, col in enumerate(cols):
    tree.heading(col, text=col)
    if col == "Miner":
        tree.column(col, width=275, anchor="w")
    elif col == "Last Active":
        tree.column(col, width=150, anchor="center")
    else:
        tree.column(col, width=80, anchor="center")
tree.pack(side="left")

scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
tree.configure(yscrollcommand=scrollbar.set)
scrollbar.pack(side="right", fill="y")

tk.Button(dashboard_tab, text="Refresh Now", command=update_table).pack(pady=10)

sort_button = tk.Button(dashboard_tab, text="Sort by Precommit %", command=toggle_sort_by_percentage)
sort_button.pack(pady=10)

countdown_label = tk.Label(dashboard_tab, text="")
countdown_label.pack()

# Add Miner Tab
add_miner_tab = ttk.Frame(notebook)
notebook.add(add_miner_tab, text="Add Miner")

miner_frame = tk.Frame(add_miner_tab)
tk.Label(miner_frame, text="Add Miner ID").pack()
miner_id_entry = tk.Entry(miner_frame, width=20)
miner_id_entry.pack()
tk.Button(miner_frame, text="Add Miner", command=lambda: (save_miner(miner_id_entry.get()), update_table())).pack()
miner_frame.pack(padx=10, pady=10)

# Settings Tab
settings_tab = ttk.Frame(notebook)
notebook.add(settings_tab, text="Settings")

options_frame = tk.Frame(settings_tab)
options_frame.pack(pady=10)

# Auto-Update Section
auto_frame = tk.Frame(options_frame)
auto_var = tk.BooleanVar(value=False)
tk.Checkbutton(auto_frame, text="Enable Auto Refresh", variable=auto_var, command=auto_update).pack()
refresh_interval = ttk.Combobox(auto_frame, values=["3", "5", "10", "15"], width=5)
refresh_interval.set("10")
refresh_interval.pack()
tk.Label(auto_frame, text="Minutes").pack()
auto_frame.pack(side="left", padx=10)

update_table()
countdown_seconds = int(refresh_interval.get()) * 60
update_countdown()

root.mainloop()
