import pandas as pd
import glob
import os
import shutil

df = pd.read_csv("dce_format.csv", sep="\t")

patients = df['Patient'].tolist()
nums = [int(x.split("_")[2]) for x in patients]

nums_test = nums[:190]
patients_test = patients[:190]
nums_train = nums[190:]
patients_train = patients[190:]

def remove_glob(folder, _patients):
    print(f"Processing folder: {folder}")
    for _p in _patients:
        print(f"Removing patient: {_p}")
        flist = glob.glob(f"{folder}/{_p}*")
        for f in flist:
            os.remove(f)
def update_glob(folder, _patients):
    print(f"Processing folder: {folder}")
    for _p in _patients:
        print(f"Updating patient: {_p}")
        flist = glob.glob(f"{folder}/{_p}*")
        flist = [f for f in flist if ".txt" in f]
        for f in flist:
            shutil.copyfile(f"test/{f.split('/')[-1]}", f)

#remove_glob("yolo_valid", patients_train)
#remove_glob("yolo_train", patients_test)
update_glob("yolo_train", patients_train)
update_glob("yolo_valid", patients_test)
