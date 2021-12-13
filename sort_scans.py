import os
from datetime import datetime
import pandas as pd
import re
import pydicom
import argparse

parse = argparse.ArgumentParser()
parse.add_argument('--input', default="processed.csv", type=str)
parse.add_argument('--output', default="processed_scantype.csv", type=str)
args = parse.parse_args()


def sort_scan(_row):
    scan_type = ''
    # Time to Echo (TE) is the time between the delivery
    # of the RF pulse and the receipt of the echo signal
    # T1: <50ms
    # DWI: 50-90ms
    # T2: >90ms
    t_echo = float(_row["Echo Time"])
    # Contrast
    contrast = _row["Contrast/Bolus Agent"]
    # DWI has non-zero b value
    bval = float(_row["DiffusionBValue"])
    # ADC has DWI-like TE
    # Perfusion has more than 1 temporal positions
    # but is otherwise like T1
    num_times = int(_row["Number of Temporal Positions"])
    # Inwash looks like T1+C
    # Outwash has trigger time >300000
    trigger = float(_row["Trigger Time"])
    desc = _row["Series Description"]

    # Logic:
    if t_echo < 50.0:
        if not contrast:
            scan_type = "T1"
        else:
            # Now sort inwash/outwash/perfusion/T1+C
            if num_times > 1:
                scan_type = "4DPERFUSION"
            if trigger > 300000:
                scan_type = "OUTWASH"

            if "sinwas" in desc.lower():
                scan_type = "INWASH"
            else:
                scan_type = "T1+C"
    elif t_echo < 90.0:
        if "adc" in desc.lower():
            scan_type = "ADC"

        if bval:
            scan_type = "DWI"
        scan_type = "UNKNOWN"
    elif t_echo > 89.9:
        scan_type = "T2"
    else:
        scan_type = "UNKNOWN"


df_total = pd.read_csv(args.input, sep="\t")
df_total["SCAN_GUESS"] = df_total.apply(lambda x: sort_scan(x), axis=1)
df_total.to_csv(args.output, sep="\t")
