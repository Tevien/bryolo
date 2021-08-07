import pandas as pd
import dicom2nifti
import cv2
import numpy as np
import nibabel as ni
import os
import shutil

'''
cols = ['Unnamed: 0' 'Patient' 'date' 'location' 'SpecificCharacterSet'
 'ImageType' 'InstanceCreationDate' 'InstanceCreationTime' 'SOPClassUID'
 'SOPInstanceUID' 'StudyDate' 'SeriesDate' 'AcquisitionDate' 'ContentDate'
 'StudyTime' 'SeriesTime' 'AcquisitionTime' 'ContentTime'
 'AccessionNumber' 'Modality' 'Manufacturer' 'ReferringPhysicianName'
 'StudyDescription' 'ProcedureCodeSequence' 'SeriesDescription'
 'ManufacturerModelName' 'PatientName' 'PatientID' 'PatientBirthDate'
 'PatientSex' 'PatientWeight' 'PatientComments' 'PatientIdentityRemoved'
 'DeidentificationMethod' 'Unnamed: 34' 'BodyPartExamined'
 'ScanningSequence' 'SequenceVariant' 'ScanOptions' 'MRAcquisitionType'
 'AngioFlag' 'SliceThickness' 'RepetitionTime' 'EchoTime'
 'NumberOfAverages' 'ImagingFrequency' 'ImagedNucleus' 'EchoNumbers'
 'MagneticFieldStrength' 'SpacingBetweenSlices'
 'NumberOfPhaseEncodingSteps' 'EchoTrainLength' 'PercentSampling'
 'PercentPhaseFieldOfView' 'PixelBandwidth' 'SoftwareVersions'
 'ProtocolName' 'DateOfLastCalibration' 'TransmitCoilName'
 'AcquisitionMatrix' 'InPlanePhaseEncodingDirection' 'FlipAngle'
 'VariableFlipAngleFlag' 'SAR' 'dBdt' 'PatientPosition' 'StudyInstanceUID'
 'SeriesInstanceUID' 'StudyID' 'SeriesNumber' 'AcquisitionNumber'
 'InstanceNumber' 'ImagePositionPatient' 'ImageOrientationPatient'
 'FrameOfReferenceUID' 'PositionReferenceIndicator' 'SliceLocation'
 'SamplesPerPixel' 'PhotometricInterpretation' 'Rows' 'Columns'
 'PixelSpacing' 'BitsAllocated' 'BitsStored' 'HighBit'
 'PixelRepresentation' 'SmallestImagePixelValue' 'LargestImagePixelValue'
 'WindowCenter' 'WindowWidth' 'RequestedProcedureDescription'
 'PerformedProcedureStepDescription'
 'FillerOrderNumberImagingServiceRequest' 'StorageMediaFileSetUID'
 'ContrastBolusAgent' 'ContrastBolusVolume' 'ContrastBolusTotalDose'
 'ContrastBolusIngredient' 'ContrastBolusIngredientConcentration'
 'PatientAge' 'PatientSize' 'PregnancyStatus' 'DeviceSerialNumber']
'''

cols = [
    'SeriesDescription', 'AcquisitionTime', 'ScanningSequence',
    'SequenceVariant', 'ScanOptions', 'MRAcquisitionType'
]


def apply(_df, func, *args):
    _df = _df[_df.apply(func, args=args, axis=1)]
    _df.reset_index(inplace=True)
    return _df


def filter_t1(x):
    if x["EchoTime"] < 12.0:
        return True
    else:
        return False


def filter_3d(x):
    if x["MRAcquisitionType"] == "3D":
        return True
    else:
        return False


def filter_patient(x, _id):
    if x["Patient"] == _id:
        return True
    else:
        return False


def make_dce_dataset(in_df, out_df):
    df_in = pd.read_csv(in_df, sep="\t")
    df_out = pd.DataFrame()
    print(f"{len(df_in)} folders to process")
    _g = df_in.groupby(["Patient", "date"])
    for combo, row in _g:
        print(f"processing {combo}")
        df_subset = df_in[(df_in["Patient"] == combo[0]) & (df_in["date"] == combo[1])]

        # Remove non T1
        df_subset = apply(df_subset, filter_t1)
        # Remove non-3D
        df_subset = apply(df_subset, filter_3d)

        # Sort on Acquisition time
        df_subset.sort_values(by=["AcquisitionTime"], inplace=True)
        print("Selected scans:")
        print(df_subset[cols].head())

        # Create combo data point
        point = {
            "Patient": combo[0],
            "date": combo[1]
        }
        for n in range(len(df_subset)):
            series_desc = df_subset.loc[n, "SeriesDescription"].replace(" ", "_")
            point[f"Image_{n}"] = '/'.join(df_subset.loc[n, "location"].split('/')[:-1])
            point["seriesDesc"] = series_desc
        df = pd.DataFrame()
        df = df.append(point, ignore_index=True)
        df_out = pd.concat([df_out, df])
    df_out.to_csv(out_df, sep="\t")
    return df_out


def write_2d_box(_coords, _outname, _class):
    assert len(_coords) == 4, "Provide [x_l, x_h, y_l, y_h]"
    _coords = [float(c) for c in _coords]
    x_l, x_h, y_l, y_h = _coords

    width = x_h-x_l
    height = y_h-y_l
    with open(_outname, "a") as f:
        f.write(f"{_class}\t{x_l}\t{y_l}\t{width}\t{height}\n")
    return True


def make_yolo_input(locs, boxes, outputdir, images=None, test=False):
    assert images, "The column name of the dicom locations is required"
    assert len(images) == 1 or len(images) == 3, "Either grayscale or RGB"

    df_locs = pd.read_csv(locs, sep="\t")
    boxes = pd.read_excel(boxes, engine="openpyxl")

    if not os.path.exists(outputdir):
        os.makedirs(outputdir)

    temp_dir = os.path.join(outputdir, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    print(boxes.head())
    for i, b in boxes.iterrows():
        patient = b["Patient ID"]
        print(f"Processing patient: {patient}")

        if test:
            test_patients = ["Breast_MRI_101", "Breast_MRI_103"]
            if patient not in test_patients:
                continue

        # Find patient dicoms
        df_patient = apply(df_locs, filter_patient, patient)
        assert len(df_patient) == 1, "More than one or no datapoints found"

        x_l, x_h, c_l, c_h, s_l, s_h = b["Start Row"], b["End Row"], b["Start Column"], \
                                       b["End Column"], b["Start Slice"], b["End Slice"]

        # Make nii
        nii_names = []
        for i in images:
            dicom_folder = df_patient.loc[0, i]
            nii_name = os.path.join(temp_dir, f"{patient}_{i}.nii.gz")
            if not os.path.exists(nii_name):
                dicom2nifti.dicom_series_to_nifti(dicom_folder, nii_name, reorient_nifti=False)
            nii_names.append(nii_name)

        # Output JPEGS
        pixels = [ni.load(n).dataobj for n in nii_names]
        pixels = [np.array(p) for p in pixels]
        pixels = [np.flip(p, 2) for p in pixels] # Annotations have slice axis reversed
        for _slice in range(np.array(pixels[0]).shape[2]):
            out_name_i = lambda i: os.path.join(outputdir, f"{patient}_{_slice}_{i}.jpg")
            out_name = os.path.join(outputdir, f"{patient}_{_slice}.jpg")
            out_name_txt = os.path.join(outputdir, f"{patient}_{_slice}.txt")
            slices = [p[:, :, _slice] for p in pixels]
            if len(slices) == 1:
                out_array = np.array(slices[0])
            else:
                out_array = np.dstack(slices)

            cv2.imwrite(out_name, out_array)
            #for i, a in zip(images, slices):
            #    out_array = np.array(a)
            #    cv2.imwrite(out_name_i(i), out_array)


            # Output txt file
            if _slice in range(s_l, s_h+1):
                write_2d_box([x_l, x_h, c_l, c_h], out_name_txt, 0)

    shutil.rmtree(temp_dir, ignore_errors=True)
    return True
