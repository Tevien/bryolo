import os
from datetime import datetime
import pandas as pd
import re
import pydicom
import argparse

DEFAULT_DATE = datetime(2013, 1, 1)

'''
# ASSUMPTIONS
- The first directory contains patients
'''


def valid_dates(dateStr):
    dates = []
    for match in re.finditer(r"\d{1,2}-\d{1,2}-\d{4}", dateStr):
        try:
            _date = datetime.strptime(match.group(0), "%m-%d-%Y")
            dates.append(_date)
        except ValueError:
            pass
    return dates


def read_header(_f):
    # Try to read header, returns 1000 if not a dicom,
    # otherwise returns the sequence in the scan
    try:
        dcm = pydicom.read_file(_f)
        try:
            print(dcm["Acquisition Number"])
        except:
            print("DICOM DOES NOT HAVE ACQUISITION NUMBER IN HEADER")
            return 1000
    except:
        return 1000


def in_dicom_dir(_dir):
    _files = os.listdir(_dir)

    ret_val = False
    file = ""
    if len(_files) < 10:
        return ret_val, file
    for f in _files:
        pos = read_header(f)
        if pos < 1000:
            ret_val = True
            if pos == 1:
                file = f
            break
    assert file, "First slice not found"
    return ret_val, file


if __name__ == '__main__':

    parse = argparse.ArgumentParser()
    parse.add_argument('--input', default="data", type=str)
    parse.add_argument('--output', default="processed.csv", type=str)
    args = parse.parse_args()

    d_patient = {
        'ID': [],
        'Date': [],
        'Description': [],
        'Location': [],
        'EchoTime': [],
        'FlipAngle': [],
        'Diff_b-val': [],
        'Duration': [],
    }

    patient_dir = args.input
    df_total = pd.DataFrame()
    patients = os.listdir(args.input)

    for p in patients:
        for root, dirs, files in os.walk(os.path.join(patient_dir, p)):
            for d in dirs:
                _dicoms, _first = in_dicom_dir(os.path.join(root, d))
                if not _dicoms:
                    continue
                else:
                    print(f"{root} &&& {d} &&& {_first}")

                # Found data point
                point = {
                    "Patient": p
                }

                full_loc = os.path.join(root, d, _first)

                path_to_dir = os.path.join(root, d)
                dates = valid_dates(str(path_to_dir).replace("/", " ").replace("MRI", " "))
                assert len(dates) == 1, "Need to do more refining"
                date = dates[0]
                point["date"] = date.strftime("%m/%d/%Y")
                point["location"] = full_loc

                # Get header from first file
                ds = pydicom.dcmread(full_loc)

                # Remove pixel data key
                keys = list(ds.keys())[:-1]

                # Add info to data point
                for k in keys:
                    v = ds[k]

                    point[v.keyword] = v.value
                df = pd.DataFrame()
                df = df.append(point, ignore_index=True)
                df_total = pd.concat([df_total, df])
    df_total.to_csv(args.output, sep="\t")
