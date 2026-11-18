from datetime import timedelta

def cycle_lengths(starts):
    # calculate the lengths of cycles based on the start dates.
    starts = sorted(starts)  # ensure the start dates are in chronological order
    lengths = []
    for i in range(len(starts) - 1):
        gap = starts[i + 1] - starts[i]
        lengths.append(gap.days)
    return lengths

def summary(lengths):
    # average shortest and longest cycle lengths returned
    return {
        "count": len(lengths),
        "average": round(sum(lengths) / len(lengths), 1),
        "shortest": min(lengths),
        "longest": max(lengths)
    }

def next_window(starts, lengths):
    # calculate the next cycle window based on last start date + shortest and longest cycles
    last = max(starts)
    earliest = last + timedelta(days=min(lengths))
    latest = last + timedelta(days=max(lengths))
    return earliest, latest

def flags(lengths):
    # return a list of flags based on cycle lengths thats worth mentioning to GP
    notes = []
    long_ones = [n for n in lengths if n > 35]
    short_ones = [n for n in lengths if n < 21]
    if long_ones:
        notes.append(f"{len(long_ones)} of {len(lengths)} cycles were longer than 35 days.")
    if short_ones:
        notes.append(f"{len(short_ones)} of {len(lengths)} cycles were shorter than 21 days.")
    return notes