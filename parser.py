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
    if not dates:
        for match in re.finditer(r"(?<!\d)\d{8}(?!\d)", dateStr):
            _date = datetime.strptime(match.group(0), "%Y%m%d")
            dates.append(_date)
    return dates


def read_breast_mr_header(_f):
    # Try to read header, returns 1000 if not a dicom,
    # otherwise returns the sequence in the scan
    _file = _f.split("/")[-1]
    try:
        ds = pydicom.filereader.dcmread(_f)
    except:
        # not a dicom
        return

    if not ds['0008', '0060'].value == 'MR':
        return

    # Check that body part is breast
    if not ds['0018', '0015'].value == 'BREAST':
        return

    loc = ds['0020', '1041'].value
    #print(_f)
    #print(loc)
    return loc


def in_dicom_dir(_dir):
    _files = os.listdir(_dir)

    ret_val = False
    file = ""
    if len(_files) < 10:
        return ret_val, file
    #print(_dir)
    for f in _files[:1]:
        pos = read_breast_mr_header(os.path.join(_dir, f))
        if pos:
            print(f"{f}_{pos}")
            ret_val = True
            file = f
            break
    if ret_val:
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
    skipped = []
    fixed_keys = None

    for p in patients[:3]:
        success = False
        for root, dirs, files in os.walk(os.path.join(patient_dir, p)):
            for d in dirs:
                _dicoms, _first = in_dicom_dir(os.path.join(root, d))
                if not _dicoms:
                    continue
                else:
                    success = True
                    print(f"{root} &&& {d} &&& {_first}")

                # Found data point
                point = {
                    "Patient": p
                }

                full_loc = os.path.join(root, d, _first)

                path_to_dir = os.path.join(root, d)
                dates = valid_dates(str(path_to_dir).replace("/", " ").replace("MRI", " "))
                assert len(dates) == 1, f"Need to do more refining, {dates}"
                date = dates[0]
                point["date"] = date.strftime("%m/%d/%Y")
                point["location"] = full_loc

                # Get header from first file
                ds = pydicom.dcmread(full_loc)

                # Remove pixel data key
                keys = list(ds.keys())[:-1]
                if not fixed_keys:
                    fixed_keys = [k for k in keys if k.group<2000]

                # Add info to data point
                for k in fixed_keys:
                    try:
                        v = ds[k]
                    except:
                        print(fixed_keys)
                        v = ds[k]

                    point[v.keyword] = v.value
                df = pd.DataFrame()
                df = df.append(point, ignore_index=True)
                df_total = pd.concat([df_total, df], axis=1)
        if not success:
            skipped.append(p)
    print(f"Skipped: {skipped}")
    df_total.to_csv(args.output, sep="\t")
