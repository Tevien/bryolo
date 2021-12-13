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

def desc_process(_desc):
    scan_type = ""
    if "sinwas" in _desc.lower():
        scan_type = "INWASH"
    elif "suitwas" in _desc.lower():
        scan_type = "OUTWASH"
    elif "perfus" in _desc.lower():
        scan_type = "4DPERFUSION"
    elif "tfe" in _desc.lower():
        scan_type = "TFE"
    elif "adc" in _desc.lower():
        scan_type = "ADC"
    elif "dwi" in _desc.lower():
        scan_type = "DWI"

    return scan_type


def sort_scan(_row):
    scan_type = ''
    # Time to Echo (TE) is the time between the delivery
    # of the RF pulse and the receipt of the echo signal
    # T1: <50ms
    # DWI: 50-90ms
    # T2: >90ms
    t_echo = float(_row["EchoTime"])
    # Contrast
    contrast = _row["ContrastBolusAgent"]
    # DWI has non-zero b value
    bval = float(_row["DiffusionBValue"])
    # ADC has DWI-like TE
    # Perfusion has more than 1 temporal positions
    # but is otherwise like T1
    num_times = _row["NumberOfTemporalPositions"]
    if num_times == num_times:
        num_times = int(num_times)
    # Inwash looks like T1+C
    # Outwash has trigger time >300000
    trigger = _row["TriggerTime"]
    try:
        trigger = float(trigger)
    except:
        trigger = -1.0
    desc = _row["SeriesDescription"]
    dp = desc_process(desc)

    # Logic:
    if t_echo < 50.0:
        # Contrast tag is empty in the PACS scang
        if trigger<0.5:
            scan_type = "T1"
        else:
            # Now sort inwash/outwash/perfusion/T1+C
            if num_times > 1:
                scan_type = "4DPERFUSION"
            if trigger > 300000:
                scan_type = "OUTWASH"

            if dp:
                scan_type = dp
            else:
                scan_type = "T1+C"
    elif t_echo < 90.0:
        if "adc" in desc.lower():
            scan_type = "ADC"

        if bval:
            scan_type = "DWI"
        elif dp:
            scan_type = dp
        else:
            scan_type = "UNKNOWN"
    elif t_echo > 89.9:
        if dp:
            scan_type = dp
        else:
            scan_type = "T2"
    else:
        if dp:
            scan_type = dp
        else:
            scan_type = "UNKNOWN"

    return scan_type


df_total = pd.read_csv(args.input, sep="\t")
df_total["SCAN_GUESS"] = df_total.apply(lambda x: sort_scan(x), axis=1)
df_total.to_csv(args.output, sep="\t")
