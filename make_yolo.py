from utils import make_dce_dataset, make_yolo_input
import argparse

if __name__ == '__main__':

    parse = argparse.ArgumentParser()
    parse.add_argument('--processed', default="processed.csv", type=str)
    parse.add_argument('--dce_dset', default="dce_format.csv", type=str)
    parse.add_argument('--boxes', default="Annotation_Boxes.xlsx", type=str)
    parse.add_argument('--output', default="test", type=str)
    args = parse.parse_args()

    #make_dce_dataset(args.processed, args.dce_dset)
    make_yolo_input(args.dce_dset, args.boxes, args.output, ["Image_0", "Image_1", "Image_2"])
