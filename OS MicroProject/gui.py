import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Scheduling algorithms are defined in main.py. This GUI only calls them.
from main import fcfs, sjf, round_robin, priority_scheduling

# ---------------------------- App data ----------------------------
DEFAULT_PROCESSES = [
    {"pid": "P1", "arrival": 0, "burst": 5, "priority": 2},
    {"pid": "P2", "arrival": 1, "burst": 3, "priority": 1},
    {"pid": "P3", "arrival": 2, "burst": 8, "priority": 3},
    {"pid": "P4", "arrival": 3, "burst": 2, "priority": 4},
]
processes = [p.copy() for p in DEFAULT_PROCESSES]
all_results = {}
all_segments = {}
editing_pid = None
graph_canvas = None

# ---------------------------- Theme ----------------------------
BG = "#F3F6FC"
CARD = "#FFFFFF"
NAVY = "#142746"
BLUE = "#2864E8"
BLUE_DARK = "#194BB8"
TEAL = "#0E9F8A"
ORANGE = "#E58A19"
RED = "#D64545"
TEXT = "#26364D"
MUTED = "#68778D"
BORDER = "#D8E1EF"
PURPLE = "#7654D6"

root = tk.Tk()
root.title("CPU Scheduling Analyzer | OS Micro-Project")
root.geometry("1120x700")
root.minsize(900, 580)
root.configure(bg=BG)

style = ttk.Style()
style.theme_use("clam")
style.configure(".", font=("Segoe UI", 10))
style.configure("TFrame", background=BG)
style.configure("TLabel", background=BG, foreground=TEXT)
style.configure("TNotebook", background=BG, borderwidth=0)
style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(16, 8),
                background="#E4EAF4", foreground=TEXT)
style.map("TNotebook.Tab", background=[("selected", CARD)],
          foreground=[("selected", BLUE_DARK)])
style.configure("Treeview", rowheight=30, font=("Segoe UI", 10),
                background=CARD, fieldbackground=CARD, foreground=TEXT,
                bordercolor=BORDER)
style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"),
                background="#E7EDF7", foreground=NAVY, padding=8)
style.map("Treeview", background=[("selected", "#D9E7FF")],
          foreground=[("selected", NAVY)])
style.configure("TEntry", padding=7)
style.configure("TCombobox", padding=6)
style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"),
                padding=(14, 10), background=BLUE, foreground="white")
style.map("Primary.TButton", background=[("active", BLUE_DARK), ("pressed", BLUE_DARK)],
          foreground=[("active", "white")])
style.configure("Success.TButton", font=("Segoe UI", 10, "bold"),
                padding=(14, 10), background=TEAL, foreground="white")
style.map("Success.TButton", background=[("active", "#087C6C")],
          foreground=[("active", "white")])
style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"),
                padding=(12, 9), background=RED, foreground="white")
style.map("Danger.TButton", background=[("active", "#B93232")],
          foreground=[("active", "white")])
style.configure("Secondary.TButton", font=("Segoe UI", 10, "bold"),
                padding=(12, 9), background="#E5ECF7", foreground=NAVY)
style.map("Secondary.TButton", background=[("active", "#D5E1F2")])

# ---------------------------- Helpers ----------------------------
def title_block(parent, title, subtitle=""):
    tk.Label(parent, text=title, font=("Segoe UI", 19, "bold"),
             bg=BG, fg=NAVY).pack(anchor="w")
    if subtitle:
        tk.Label(parent, text=subtitle, font=("Segoe UI", 10),
                 bg=BG, fg=MUTED).pack(anchor="w", pady=(4, 14))

def card(parent, **kwargs):
    return tk.Frame(parent, bg=CARD, highlightbackground=BORDER,
                    highlightthickness=1, **kwargs)

def average(results, key):
    return sum(row[key] for row in results) / len(results) if results else 0

def calculate_metrics(results):
    if not results:
        return 0.0, 0.0
    total_burst = sum(p["burst"] for p in results)
    finish_time = max(p["completion"] for p in results)
    if finish_time <= 0:
        return 0.0, 0.0
    return total_burst / finish_time * 100, len(results) / finish_time

def invalidate_results():
    global all_results, all_segments, graph_canvas
    all_results, all_segments = {}, {}
    for item in result_table.get_children():
        result_table.delete(item)
    summary_var.set("Process data changed. Run the simulation to refresh results.")
    metrics_var.set("CPU utilization and throughput will appear here.")
    if graph_canvas:
        graph_canvas.get_tk_widget().destroy()
        graph_canvas = None
    graph_placeholder.pack(expand=True, pady=20)

def refresh_process_table(select_pid=None):
    for item in process_table.get_children():
        process_table.delete(item)
    for p in processes:
        process_table.insert("", "end", iid=p["pid"],
            values=(p["pid"], p["arrival"], p["burst"], p["priority"]))
    if select_pid and select_pid in process_table.get_children():
        process_table.selection_set(select_pid)
        process_table.focus(select_pid)
    process_count_var.set(f"{len(processes)} process(es)")

def clear_form():
    global editing_pid
    editing_pid = None
    defaults = {"Process ID": f"P{len(processes) + 1}", "Arrival Time": "0",
                "Burst Time": "4", "Priority": "2"}
    for label, entry in entries.items():
        entry.delete(0, "end")
        entry.insert(0, defaults[label])
    add_button.configure(text="＋ Add Process")
    process_table.selection_remove(process_table.selection())

def on_process_select(_event=None):
    global editing_pid
    selected = process_table.selection()
    if not selected:
        return
    pid = selected[0]
    process = next((p for p in processes if p["pid"] == pid), None)
    if process is None:
        return
    editing_pid = pid
    values = {"Process ID": process["pid"], "Arrival Time": str(process["arrival"]),
              "Burst Time": str(process["burst"]), "Priority": str(process["priority"])}
    for label, value in values.items():
        entries[label].delete(0, "end")
        entries[label].insert(0, value)
    add_button.configure(text="✓ Save Changes")

def add_or_update_process():
    global editing_pid
    pid = entries["Process ID"].get().strip()
    try:
        arrival = int(entries["Arrival Time"].get())
        burst = int(entries["Burst Time"].get())
        priority = int(entries["Priority"].get())
        if not pid or any(ch.isspace() for ch in pid):
            raise ValueError("Process ID must be non-empty and contain no spaces.")
        if arrival < 0 or burst <= 0 or priority <= 0:
            raise ValueError("Arrival must be >= 0; burst and priority must be > 0.")
        if any(p["pid"] == pid and p["pid"] != editing_pid for p in processes):
            raise ValueError("That process ID already exists.")
        new_process = {"pid": pid, "arrival": arrival, "burst": burst, "priority": priority}
        if editing_pid:
            for index, process in enumerate(processes):
                if process["pid"] == editing_pid:
                    processes[index] = new_process
                    break
        else:
            processes.append(new_process)
        clear_form()
        refresh_process_table()
        invalidate_results()
        status_var.set(f"{pid} saved. Run a simulation to calculate results.")
    except ValueError as error:
        messagebox.showerror("Invalid Process", str(error))

def remove_process():
    selected = process_table.selection()
    if not selected:
        messagebox.showinfo("Select Process", "Select a process row first.")
        return
    pid = selected[0]
    processes[:] = [p for p in processes if p["pid"] != pid]
    clear_form()
    refresh_process_table()
    invalidate_results()
    status_var.set(f"{pid} removed.")

def clear_all_processes():
    if not processes:
        return
    if messagebox.askyesno("Clear Processes", "Remove every process?"):
        processes.clear()
        clear_form()
        refresh_process_table()
        invalidate_results()
        status_var.set("All processes cleared.")

def run_simulation():
    global all_results, all_segments
    if not processes:
        messagebox.showerror("No Processes", "Add at least one process first.")
        return
    try:
        quantum = int(quantum_entry.get())
        if quantum <= 0:
            raise ValueError("Time quantum must be a positive integer.")
    except ValueError as error:
        messagebox.showerror("Invalid Time Quantum", str(error) if str(error) else
                             "Time quantum must be a positive integer.")
        return

    runners = {
        "FCFS": lambda: fcfs(processes),
        "SJF": lambda: sjf(processes),
        "Round Robin": lambda: round_robin(processes, quantum),
        "Priority": lambda: priority_scheduling(processes),
    }
    selected = algorithm_var.get()
    names = list(runners) if selected == "All Algorithms" else [selected]
    try:
        new_results, new_segments = {}, {}
        for name in names:
            results, segments = runners[name]()
            new_results[name] = results
            new_segments[name] = segments
        all_results, all_segments = new_results, new_segments
    except (ValueError, KeyError, IndexError) as error:
        messagebox.showerror("Simulation Error", str(error))
        return

    for item in result_table.get_children():
        result_table.delete(item)
    for name, results in all_results.items():
        for row in results:
            result_table.insert("", "end", values=(
                name, row["pid"], row["arrival"], row["burst"], row["priority"],
                row["completion"], row["turnaround"], row["waiting"]))
    summaries, metric_lines, waiting_averages = [], [], {}
    for name, results in all_results.items():
        avg_wt, avg_tat = average(results, "waiting"), average(results, "turnaround")
        cpu, throughput = calculate_metrics(results)
        waiting_averages[name] = avg_wt
        summaries.append(f"{name}:  Average WT = {avg_wt:.2f}  |  Average TAT = {avg_tat:.2f}")
        metric_lines.append(f"{name}: CPU utilization = {cpu:.2f}%  |  Throughput = {throughput:.4f} processes/time unit")
    best = min(waiting_averages, key=waiting_averages.get) if waiting_averages else ""
    best_text = (f"Lowest average waiting time: {best} ({waiting_averages[best]:.2f} units)"
                 if len(all_results) > 1 else "Select 'All Algorithms' to compare all four algorithms.")
    summary_var.set("\n".join(summaries))
    metrics_var.set(best_text + "\n" + "\n".join(metric_lines))
    status_var.set("Simulation complete. Results and visualizations are updated.")
    notebook.select(results_tab)

def export_results():
    if not all_results:
        messagebox.showinfo("No Results", "Run a simulation before exporting.")
        return
    path = filedialog.asksaveasfilename(title="Export Scheduling Results",
        defaultextension=".csv", filetypes=[("CSV files", "*.csv")],
        initialfile="cpu_scheduling_results.csv")
    if not path:
        return
    try:
        with open(path, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(["Algorithm", "Process ID", "Arrival", "Burst", "Priority",
                             "Completion", "Turnaround", "Waiting", "CPU Utilization (%)",
                             "Throughput (processes/time unit)"])
            for name, results in all_results.items():
                cpu, throughput = calculate_metrics(results)
                for p in results:
                    writer.writerow([name, p["pid"], p["arrival"], p["burst"], p["priority"],
                                     p["completion"], p["turnaround"], p["waiting"],
                                     f"{cpu:.2f}", f"{throughput:.4f}"])
            writer.writerow([])
            writer.writerow(["Algorithm", "Average Waiting Time", "Average Turnaround Time"])
            for name, results in all_results.items():
                writer.writerow([name, f"{average(results, 'waiting'):.2f}",
                                 f"{average(results, 'turnaround'):.2f}"])
        messagebox.showinfo("Export Complete", f"Results saved to:\n{path}")
    except OSError as error:
        messagebox.showerror("Export Failed", str(error))

def show_graph():
    global graph_canvas
    if not all_results:
        messagebox.showinfo("Run Simulation", "Run a simulation before opening charts.")
        return
    if graph_canvas:
        graph_canvas.get_tk_widget().destroy()
        graph_canvas = None
    graph_placeholder.pack_forget()
    fig, ax = plt.subplots(figsize=(10, 5))
    choice = graph_type.get()
    names = list(all_results)
    if choice == "Gantt Charts":
        palette = plt.get_cmap("tab20")
        for index, name in enumerate(names):
            y = len(names) - index - 1
            segments = all_segments[name]
            for j, (pid, start, end) in enumerate(segments):
                color_idx = (int(pid[1:]) - 1) % 20 if pid.startswith("P") and pid[1:].isdigit() else j % 20
                ax.barh(y, end-start, left=start, height=0.58,
                        color=palette(color_idx), edgecolor="white")
                ax.text((start+end)/2, y, pid, ha="center", va="center", fontsize=8)
            if segments:
                for pid, start, end in segments:
                    ax.text(start, y-0.34, str(start), ha="center", va="top", fontsize=8)
                ax.text(segments[-1][2], y-0.34, str(segments[-1][2]), ha="center", va="top", fontsize=8)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(list(reversed(names)))
        ax.set_xlabel("Time Units")
        ax.set_title("CPU Execution Timeline — Gantt Chart", fontweight="bold", pad=14)
        ax.grid(axis="x", linestyle="--", alpha=0.25)
        ax.set_axisbelow(True)
    else:
        key = "waiting" if choice == "Average Waiting Time" else "turnaround"
        values = [average(all_results[n], key) for n in names]
        bars = ax.bar(names, values, color=[BLUE, TEAL, ORANGE, PURPLE][:len(names)])
        ax.bar_label(bars, fmt="%.2f", padding=4, fontweight="bold")
        ax.set_title(choice + " by Algorithm", fontweight="bold", pad=14)
        ax.set_ylabel("Time Units")
        ax.grid(axis="y", linestyle="--", alpha=0.25)
        ax.set_axisbelow(True)
        ax.margins(y=0.18)
    fig.tight_layout()
    graph_canvas = FigureCanvasTkAgg(fig, master=graph_frame)
    graph_canvas.draw()
    graph_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
    plt.close(fig)

def show_help():
    messagebox.showinfo("Quick Guide",
        "1. Add, edit, or remove processes in the Processes tab.\n"
        "2. Select one algorithm or All Algorithms.\n"
        "3. Set a positive time quantum for Round Robin.\n"
        "4. Click Run Simulation to populate Results.\n"
        "5. Open Visualizations and click Show Graph.\n"
        "6. Export Results saves the current results as CSV.\n\n"
        "Priority rule: a smaller number means higher priority.")

# ---------------------------- Header ----------------------------
header = tk.Frame(root, bg=NAVY, height=82)
header.pack(fill="x")
header.pack_propagate(False)
header_left = tk.Frame(header, bg=NAVY)
header_left.pack(side="left", padx=22, pady=12)
tk.Label(header_left, text="CPU SCHEDULING ANALYZER",
         font=("Segoe UI", 19, "bold"), bg=NAVY, fg="white").pack(anchor="w")
tk.Label(header_left, text="OPERATING SYSTEMS  •  MICRO-PROJECT",
         font=("Segoe UI", 10, "bold"), bg=NAVY, fg="#C8D8F4").pack(anchor="w", pady=(4, 0))
tk.Label(header, text="4 ALGORITHMS", font=("Segoe UI", 10, "bold"),
         bg="#294C7D", fg="white", padx=16, pady=9).pack(side="right", padx=28)

# ---------------------------- Tabs ----------------------------
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=12, pady=(8, 5))
process_tab = tk.Frame(notebook, bg=BG, padx=12, pady=10)
results_tab = tk.Frame(notebook, bg=BG, padx=12, pady=10)
graphs_tab = tk.Frame(notebook, bg=BG, padx=12, pady=10)
about_tab = tk.Frame(notebook, bg=BG, padx=12, pady=10)
notebook.add(process_tab, text="  ⚙ Processes  ")
notebook.add(results_tab, text="  ▤ Results  ")
notebook.add(graphs_tab, text="  ▥ Visualizations  ")
notebook.add(about_tab, text="  ℹ About  ")

# ---------------------------- Processes tab ----------------------------
title_block(process_tab, "Manage Processes", "Add processes or select a row to edit or remove it.")
form = card(process_tab, padx=10, pady=8)
form.pack(fill="x", pady=(0, 12))
fields = [("Process ID", "P5"), ("Arrival Time", "0"), ("Burst Time", "4"), ("Priority", "2")]
entries = {}
for col, (label, default) in enumerate(fields):
    tk.Label(form, text=label, bg=CARD, fg=TEXT, font=("Segoe UI", 9, "bold")).grid(
        row=0, column=col, sticky="w", padx=7, pady=(0, 5))
    entry = ttk.Entry(form)
    entry.insert(0, default)
    entry.grid(row=1, column=col, sticky="ew", padx=7, pady=(0, 4))
    entries[label] = entry
    form.columnconfigure(col, weight=1)
add_button = ttk.Button(form, text="＋ Add Process", command=add_or_update_process, style="Success.TButton")
add_button.grid(row=1, column=4, padx=(8, 4), sticky="ew")
form.columnconfigure(4, weight=0)

process_card = card(process_tab, padx=8, pady=7)
process_card.pack(fill="both", expand=False)
process_header = tk.Frame(process_card, bg=CARD)
process_header.pack(fill="x", pady=(0, 6))
tk.Label(process_header, text="Process List", bg=CARD, fg=NAVY,
         font=("Segoe UI", 12, "bold")).pack(side="left")
process_count_var = tk.StringVar(value="")
tk.Label(process_header, textvariable=process_count_var, bg=CARD, fg=MUTED).pack(side="right")
process_columns = ("pid", "arrival", "burst", "priority")
process_table = ttk.Treeview(process_card, columns=process_columns, show="headings",
                             height=5, selectmode="browse")
for col, label in zip(process_columns, ("Process ID", "Arrival Time", "Burst Time", "Priority")):
    process_table.heading(col, text=label)
    process_table.column(col, anchor="center", width=160)
process_table.pack(fill="both", expand=True)
process_table.bind("<<TreeviewSelect>>", on_process_select)

process_buttons = tk.Frame(process_tab, bg=BG)
process_buttons.pack(fill="x", pady=(6, 0))
ttk.Button(process_buttons, text="✕ Remove Selected", command=remove_process,
           style="Danger.TButton").pack(side="left", padx=(0, 8))
ttk.Button(process_buttons, text="Clear All", command=clear_all_processes,
           style="Secondary.TButton").pack(side="left", padx=4)
ttk.Button(process_buttons, text="New / Cancel Edit", command=clear_form,
           style="Secondary.TButton").pack(side="left", padx=4)
tk.Label(process_buttons, text="Priority: smaller number = higher priority",
         bg=BG, fg=MUTED).pack(side="right")

# Algorithm controls are shared across tabs and visible on Processes tab
controls = card(process_tab, padx=12, pady=10)
controls.pack(fill="x", pady=(7, 0))
tk.Label(controls, text="Scheduling Algorithm", bg=CARD, fg=NAVY,
         font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 8))
algorithm_var = tk.StringVar(value="All Algorithms")
algorithm_choice = ttk.Combobox(controls, textvariable=algorithm_var,
    values=["All Algorithms", "FCFS", "SJF", "Round Robin", "Priority"],
    state="readonly", width=19)
algorithm_choice.pack(side="left", padx=(0, 18))
tk.Label(controls, text="Round Robin Quantum", bg=CARD, fg=NAVY,
         font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 8))
quantum_entry = ttk.Entry(controls, width=7)
quantum_entry.insert(0, "2")
quantum_entry.pack(side="left")
ttk.Button(controls, text="▶  RUN SIMULATION", command=run_simulation,
           style="Primary.TButton").pack(side="right", padx=(10, 0))

# ---------------------------- Results tab ----------------------------
title_block(results_tab, "Scheduling Results",
            "Completion, turnaround and waiting times calculated by the algorithms in main.py.")
result_card = card(results_tab, padx=10, pady=10)
result_card.pack(fill="both", expand=True)
result_columns = ("algorithm", "pid", "arrival", "burst", "priority", "completion", "turnaround", "waiting")
result_titles = {"algorithm": "Algorithm", "pid": "Process", "arrival": "Arrival",
                 "burst": "Burst", "priority": "Priority", "completion": "Completion",
                 "turnaround": "Turnaround", "waiting": "Waiting"}
result_table = ttk.Treeview(result_card, columns=result_columns, show="headings", height=11)
for col in result_columns:
    result_table.heading(col, text=result_titles[col])
    result_table.column(col, width=110, anchor="center")
result_table.pack(fill="both", expand=True)
summary_var = tk.StringVar(value="Run a simulation to view average waiting and turnaround times.")
summary_box = tk.Label(results_tab, textvariable=summary_var, bg="#E5EEFF", fg=NAVY,
                       font=("Segoe UI", 10, "bold"), justify="left", anchor="w",
                       padx=14, pady=12)
summary_box.pack(fill="x", pady=(12, 8))
metrics_var = tk.StringVar(value="CPU utilization and throughput will appear here.")
metrics_box = tk.Label(results_tab, textvariable=metrics_var, bg=CARD, fg=TEXT,
                       font=("Segoe UI", 10), justify="left", anchor="w",
                       padx=14, pady=12, highlightbackground=BORDER, highlightthickness=1)
metrics_box.pack(fill="x")
ttk.Button(results_tab, text="⇩ Export Results to CSV", command=export_results,
           style="Success.TButton").pack(anchor="e", pady=(10, 0))

# ---------------------------- Visualizations tab ----------------------------
title_block(graphs_tab, "Visualizations", "Compare algorithm performance or inspect execution order with Gantt charts.")
graph_controls = tk.Frame(graphs_tab, bg=BG)
graph_controls.pack(fill="x", pady=(0, 10))
graph_type = tk.StringVar(value="Gantt Charts")
graph_choice = ttk.Combobox(graph_controls, textvariable=graph_type,
    values=["Average Waiting Time", "Average Turnaround Time", "Gantt Charts"],
    state="readonly", width=28)
graph_choice.pack(side="left", padx=(0, 10))
ttk.Button(graph_controls, text="▥  SHOW GRAPH", command=show_graph,
           style="Primary.TButton").pack(side="left")
ttk.Button(graph_controls, text="Quick Guide", command=show_help,
           style="Secondary.TButton").pack(side="right")
graph_frame = card(graphs_tab, padx=8, pady=8)
graph_frame.pack(fill="both", expand=True)
graph_placeholder = tk.Label(graph_frame,
    text="Run a simulation, then click SHOW GRAPH.\nGantt charts show the execution timeline for each selected algorithm.",
    bg=CARD, fg=MUTED, font=("Segoe UI", 12), justify="center")
graph_placeholder.pack(expand=True, pady=20)

# ---------------------------- About tab ----------------------------
title_block(about_tab, "About This Project", "A visual learning tool for CPU scheduling in operating systems.")
about_card = card(about_tab, padx=20, pady=18)
about_card.pack(fill="x", pady=(0, 14))
tk.Label(about_card, text="PROJECT OVERVIEW", font=("Segoe UI", 11, "bold"),
         bg=CARD, fg=BLUE).pack(anchor="w")
tk.Label(about_card,
    text=("The CPU Scheduling Analyzer simulates how an operating system selects processes for CPU execution. "
          "It calculates completion, turnaround and waiting times, compares CPU utilization and throughput, "
          "shows Gantt charts and can export results to CSV."),
    wraplength=1000, justify="left", font=("Segoe UI", 11), bg=CARD, fg=TEXT
).pack(anchor="w", pady=(8, 18))
for name, desc in [
    ("FCFS", "First Come, First Served — executes in arrival order."),
    ("SJF", "Shortest Job First — chooses the available process with the shortest burst."),
    ("Round Robin", "Gives each ready process a fixed time slice called the time quantum."),
    ("Priority", "Chooses the available process with the highest priority; smaller number means higher priority.")
]:
    row = tk.Frame(about_card, bg=CARD)
    row.pack(fill="x", pady=5)
    tk.Label(row, text=name, width=16, anchor="w", font=("Segoe UI", 10, "bold"),
             bg=CARD, fg=NAVY).pack(side="left")
    tk.Label(row, text=desc, wraplength=900, justify="left",
             bg=CARD, fg=TEXT).pack(side="left", fill="x", expand=True)
formula_card = tk.Frame(about_tab, bg="#E5EEFF", padx=18, pady=14)
formula_card.pack(fill="x")
tk.Label(formula_card, text="KEY FORMULAS", bg="#E5EEFF", fg=NAVY,
         font=("Segoe UI", 11, "bold")).pack(anchor="w")
tk.Label(formula_card,
         text="Turnaround Time = Completion Time − Arrival Time\nWaiting Time = Turnaround Time − Burst Time",
         bg="#E5EEFF", fg=TEXT, font=("Segoe UI", 11), justify="left").pack(anchor="w", pady=(6, 0))

# ---------------------------- Footer/status ----------------------------
footer = tk.Frame(root, bg=NAVY, padx=12, pady=6)
footer.pack(fill="x", side="bottom")
status_var = tk.StringVar(value="Ready. Add processes and click RUN SIMULATION.")
tk.Label(footer, textvariable=status_var, bg=NAVY, fg="#E0E9F8",
         font=("Segoe UI", 9)).pack(side="left")
tk.Label(footer, text="FCFS  •  SJF  •  ROUND ROBIN  •  PRIORITY",
         bg=NAVY, fg="#C8D8F4", font=("Segoe UI", 9, "bold")).pack(side="right")

refresh_process_table()
root.mainloop()
