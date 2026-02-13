import xml.etree.ElementTree as ET
import shutil
from glob import glob
import os
import cv2

# ================================================
# CONFIGURATION
# Classe finale
FINAL_CLASSES = ["car"]

# UA-DETRAC types autorisés
KEEP_TYPES = ["car", "van"]   # fusionnés
IGNORE_TYPES = ["bus", "others"]

# Frame sampling (anti-overfitting vidéo)
FRAME_STRIDE = 5   # ← clé du fix (1 frame sur 5)

# Paths
ann_train = "/kaggle/input/ua-detrac-orig/DETRAC-Train-Annotations-XML/DETRAC-Train-Annotations-XML"
ann_val   = "/kaggle/input/ua-detrac-orig/DETRAC-Test-Annotations-XML/DETRAC-Test-Annotations-XML"
img_root  = "/kaggle/input/ua-detrac-orig/DETRAC-Images/DETRAC-Images"

out_images_train = "data/images/train"
out_labels_train = "data/labels/train"
out_images_val   = "data/images/val"
out_labels_val   = "data/labels/val"

for d in [
    out_images_train, out_labels_train,
    out_images_val, out_labels_val
]:
    os.makedirs(d, exist_ok=True)

# ==================================================
# CLASS MAPPING
# ==================================================

def map_vehicle_type(vtype):
    """
    car  -> 0
    van  -> 0
    bus / others -> ignored
    """
    if vtype in KEEP_TYPES:
        return 0
    return None

# ==================================================
# CONVERSION BOX
# ==================================================

def convert_to_yolo(left, top, width, height, img_w, img_h):
    xmin = float(left)
    ymin = float(top)
    xmax = xmin + float(width)
    ymax = ymin + float(height)

    return (
        ((xmin + xmax) / 2) / img_w,
        ((ymin + ymax) / 2) / img_h,
        (xmax - xmin) / img_w,
        (ymax - ymin) / img_h
    )

# ==================================================
# XML PROCESSING
# ==================================================

def process_xml(xml_path, mode="train"):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    seq_name = root.attrib["name"]
    img_dir = os.path.join(img_root, seq_name)

    out_img_dir = out_images_train if mode == "train" else out_images_val
    out_lbl_dir = out_labels_train if mode == "train" else out_labels_val

    for frame in root.findall("frame"):
        frame_num = int(frame.attrib["num"])

        # FRAME SAMPLING (clé anti-overfitting)
        if frame_num % FRAME_STRIDE != 0:
            continue

        img_name = f"img{frame_num:05d}.jpg"
        img_path = os.path.join(img_dir, img_name)

        if not os.path.exists(img_path):
            continue

        img = cv2.imread(img_path)
        if img is None:
            continue
        h, w = img.shape[:2]

        target_list = frame.find("target_list")
        label_lines = []

        if target_list is not None:
            for obj in target_list.findall("target"):
                attr = obj.find("attribute")
                if attr is None:
                    continue

                vtype = attr.attrib.get("vehicle_type")
                cls_id = map_vehicle_type(vtype)

                if cls_id is None:
                    continue

                box = obj.find("box")
                if box is None:
                    continue

                x, y, bw, bh = convert_to_yolo(
                    box.attrib["left"],
                    box.attrib["top"],
                    box.attrib["width"],
                    box.attrib["height"],
                    w, h
                )

                label_lines.append(
                    f"{cls_id} {x:.6f} {y:.6f} {bw:.6f} {bh:.6f}"
                )

        out_name = f"{seq_name}_img{frame_num:05d}"

        # écrire label même vide (image négative)
        with open(os.path.join(out_lbl_dir, out_name + ".txt"), "w") as f:
            if label_lines:
                f.write("\n".join(label_lines))

        dst_img = os.path.join(out_img_dir, out_name + ".jpg")
        if not os.path.exists(dst_img):
            shutil.copy(img_path, dst_img)

# ==================================================
# EXECUTION
# ==================================================

print("Conversion TRAIN (frame sampling activé)...")
for xml_file in glob(os.path.join(ann_train, "*.xml")):
    process_xml(xml_file, mode="train")

print("Conversion VAL (frame sampling activé)...")
for xml_file in glob(os.path.join(ann_val, "*.xml")):
    process_xml(xml_file, mode="val")

print("Dataset YOLO UA-DETRAC (car + van) prêt — frame redundancy réduite.")