import argparse, os
from pathlib import Path
from utils.utils import make_yolo_inf
import torch
from utils.general import non_max_suppression, scale_coords, xyxy2xywh, increment_path
from utils.plots import colors, plot_one_box
from models.experimental import attempt_load
from utils.datasets import LoadImages
from utils.torch_utils import select_device


def parse_opt():
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', nargs='+', type=str, default='/DATA/sb/BREAST/yolov5/runs/train/exp3/weights/best.pt', help='model.pt path(s)')
    parser.add_argument('--save_dir', nargs='+', type=str, default='yolo_valid_output', help='Saving output')
    parser.add_argument('--dicom_df', nargs='+', type=str, default='processed_valid.csv', help='Location of valid dicoms')
    parser.add_argument('--jpg_loc', type=str, default='yolo_valid', help='file/dir/URL/glob, 0 for webcam')
    parser.add_argument('--imgsz', '--img', '--img-size', type=int, default=448, help='inference size (pixels)')
    parser.add_argument('--conf-thres', type=float, default=0.25, help='confidence threshold')
    parser.add_argument('--iou-thres', type=float, default=0.45, help='NMS IoU threshold')
    parser.add_argument('--max-det', type=int, default=1000, help='maximum detections per image')
    parser.add_argument('--device', default='', help='cuda device, i.e. 0 or 0,1,2,3 or cpu')
    parser.add_argument('--augment', action='store_true', help='augmented inference')
    parser.add_argument('--visualize', action='store_true', help='visualize features')
    parser.add_argument('--classes', nargs='+', type=int, help='filter by class: --class 0, or --class 0 2 3')
    parser.add_argument('--agnostic-nms', action='store_true', help='class-agnostic NMS')
    opt = parser.parse_args()
    return opt


def main(weights='yolov5s.pt',  # model.pt path(s) ###
         dicom_df="processed_valid.csv", ###
         jpg_loc='yolo_valid',  # file/dir/URL/glob, 0 for webcam ###
         imgsz=448,  # inference size (pixels) ###
         conf_thres=0.25,  # confidence threshold ###
         iou_thres=0.45,  # NMS IOU threshold ###
         max_det=1000,  # maximum detections per image ###
         device='',  # cuda device, i.e. 0 or 0,1,2,3 or cpu ###
         augment=False, ###
         classes=None,  # filter by class: --class 0, or --class 0 2 3 ###
         agnostic_nms=False,  # class-agnostic NMS ###
         save_dir='yolo_valid_output', ###
         visualize=False  # visualize features ###
         ):
    # Make the image directory
    make_yolo_inf(dicom_df, jpg_loc, images=["Image_0", "Image_1", "Image_2"])

    device = select_device(device)

    w = weights[0] if isinstance(weights, list) else weights
    stride, names = 64, [f'class{i}' for i in range(1000)]  # assign defaults
    model = attempt_load(weights, map_location=device)  # load FP32 model
    stride = int(model.stride.max())  # model stride
    names = model.module.names if hasattr(model, 'module') else model.names  # get class names

    dataset = LoadImages(jpg_loc, img_size=imgsz, stride=stride)
    bs = 1  # batch_size

    model(torch.zeros(1, 3, imgsz, imgsz).to(device).type_as(next(model.parameters())))  # run once
    for path, img, im0s, vid_cap in dataset:
        img = torch.from_numpy(img).to(device)
        img = img.float()
        img /= 255.0  # 0 - 255 to 0.0 - 1.0
        if len(img.shape) == 3:
            img = img[None]  # expand for batch dim

        visualize = increment_path(save_dir / Path(path).stem, mkdir=True) if visualize else False
        pred = model(img, augment=augment, visualize=visualize)[0]
        pred = non_max_suppression(pred, conf_thres, iou_thres, classes, agnostic_nms, max_det=max_det)

        # Process predictions
        for i, det in enumerate(pred):  # detections per image
            p, s, im0, frame = path, '', im0s.copy(), getattr(dataset, 'frame', 0)

            p = Path(p)  # to Path
            #save_path = os.path.join(save_dir, p.name)  # img.jpg
            txt_path = os.path.join(save_dir, 'labels', p.stem)
            s += '%gx%g ' % img.shape[2:]  # print string
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            #imc = im0
            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(img.shape[2:], det[:, :4], im0.shape).round()

                # Print results
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

                # Write results
                for *xyxy, conf, cls in reversed(det):
                    xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                    line = (cls, *xywh)  # label format
                    with open(txt_path + '.txt', 'a') as f:
                        f.write(('%g ' * len(line)).rstrip() % line + '\n')

                        c = int(cls)  # integer class
                        label = names[c]
                        plot_one_box(xyxy, im0, label=label, color=colors(c, True), line_thickness=3)


if __name__ == "__main__":
    opt = parse_opt()
    main(**vars(opt))
