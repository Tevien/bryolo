import cv2
import matplotlib.pyplot as plt

patient = "Breast_MRI_103_37"
jpg_name = f"test/{patient}.jpg"
txt_name = f"test/{patient}.txt"

jpg = cv2.imread(jpg_name)
#jpg = cv2.flip(jpg, -1)
shape = jpg.shape

boxes = []
with open(txt_name) as f:
    for line in f.readlines():
        line = line.rstrip("\n")
        boxes.append(line.split("\t")[1:])

for b in boxes:
    b = [float(b1) for b1 in b]
    x, y, w, h = b
    #x = shape[0]-x
    #y = shape[1]-y

    _l = int(x)
    _r = int(x + w)
    _t = int(y + h)
    _b = int(y)
    print(f"{_l}_{_r}_{_t}_{_b}")
    print(shape)
    jpg = cv2.rectangle(jpg, (_l, _b), (_r, _t), (0, 0, 255), 6)

plt.imsave(f"test_{patient}.jpg", jpg)
