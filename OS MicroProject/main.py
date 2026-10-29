"""CPU scheduling logic for the OS micro-project.

This module is imported by gui.py. It contains the algorithms and timing
calculations; the GUI is used  for displaying results.
"""

from collections import deque

def calculate(segments, processes):
    """Calculate completion, turnaround, and waiting times for each process."""
    completion_times = {process["pid"]: 0 for process in processes}

    for pid, start, end in segments:
        completion_times[pid] = end

    results = []
    for process in processes:
        completion = completion_times[process["pid"]]
        turnaround = completion - process["arrival"]
        waiting = turnaround - process["burst"]
        results.append({
            **process,
            "completion": completion,
            "turnaround": turnaround,
            "waiting": waiting,
        })

    return results

#FCFS Algorithm 
def fcfs(processes):
    """First Come, First Served scheduling (non-preemptive)."""
    jobs = sorted(processes, key=lambda p: (p["arrival"], p["pid"]))
    segments = []
    time = 0

    for process in jobs:
        time = max(time, process["arrival"])
        start = time
        time += process["burst"]
        segments.append((process["pid"], start, time))

    return calculate(segments, processes), segments

#SJF Algorithm
def sjf(processes):
    """Non-preemptive Shortest Job First scheduling."""
    remaining = processes.copy()
    segments = []
    time = 0

    while remaining:
        available = [p for p in remaining if p["arrival"] <= time]
        if not available:
            time = min(p["arrival"] for p in remaining)
            continue

        chosen = min(available, key=lambda p: (p["burst"], p["arrival"], p["pid"]))
        start = time
        time += chosen["burst"]
        segments.append((chosen["pid"], start, time))
        remaining.remove(chosen)

    return calculate(segments, processes), segments

#Priority Scheduling Algorithm
def priority_scheduling(processes):
    """Non-preemptive priority scheduling; a smaller number means higher priority."""
    remaining = processes.copy()
    segments = []
    time = 0

    while remaining:
        available = [p for p in remaining if p["arrival"] <= time]
        if not available:
            time = min(p["arrival"] for p in remaining)
            continue

        chosen = min(available, key=lambda p: (p["priority"], p["arrival"], p["pid"]))
        start = time
        time += chosen["burst"]
        segments.append((chosen["pid"], start, time))
        remaining.remove(chosen)

    return calculate(segments, processes), segments

#Round Robin Algorithm
def round_robin(processes, quantum):
    """Round Robin scheduling using the given positive time quantum."""
    if quantum <= 0:
        raise ValueError("Time quantum must be a positive integer.")

    jobs = sorted(processes, key=lambda p: (p["arrival"], p["pid"]))
    remaining = {p["pid"]: p["burst"] for p in jobs}
    ready = deque()
    segments = []
    time = 0
    next_job = 0

    while next_job < len(jobs) or ready:

        if not ready and next_job < len(jobs):
            time = max(time, jobs[next_job]["arrival"])

        while next_job < len(jobs) and jobs[next_job]["arrival"] <= time:
            ready.append(jobs[next_job])
            next_job += 1

        process = ready.popleft()
        pid = process["pid"]
        start = time
        run_time = min(quantum, remaining[pid])
        time += run_time
        remaining[pid] -= run_time
        segments.append((pid, start, time))

        while next_job < len(jobs) and jobs[next_job]["arrival"] <= time:
            ready.append(jobs[next_job])
            next_job += 1

        if remaining[pid] > 0:
            ready.append(process)

    return calculate(segments, processes), segments
