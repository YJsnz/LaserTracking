#!/usr/bin/env python3
"""
Labelme JSON 标注 → YOLO txt 格式转换脚本。

用法:
  python labelme_to_yolo.py \
      --json-dir ../datasets/annotations \
      --image-dir ../datasets/raw_frames \
      --out-dir ../datasets/yolo_dataset \
      --labels drone

说明:
  - 读取 labelme 导出的 JSON 标注文件
  - 自动解析矩形框 (rectangle)、旋转矩形 (oriented_rectangle) 和多边形 (polygon)
  - 输出 YOLO 格式: class_id cx cy w h (归一化到 [0,1])
  - 自动将对应的图片复制到输出目录
  - 生成 classes.txt
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np


def points_to_bbox(points):
    """点列表 → YOLO 轴对齐外接框 (cx, cy, w, h)。"""
    pts = np.array(points, dtype=np.float32)
    x_min, y_min = pts.min(axis=0)
    x_max, y_max = pts.max(axis=0)
    cx = (x_min + x_max) / 2.0
    cy = (y_min + y_max) / 2.0
    w = x_max - x_min
    h = y_max - y_min
    return cx, cy, w, h


def convert_json(json_path, label_to_id, img_width, img_height):
    """
    解析单个 labelme JSON，返回 YOLO 格式行列表。
    每行: "class_id cx cy w h"（归一化）
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 优先使用 JSON 中的图像尺寸
    if "imageWidth" in data and "imageHeight" in data:
        img_w = data["imageWidth"]
        img_h = data["imageHeight"]
    else:
        img_w = img_width
        img_h = img_height

    if img_w <= 0 or img_h <= 0:
        print(f"  [WARN] {json_path}: 无法获取图像尺寸，跳过")
        return []

    lines = []
    for shape in data.get("shapes", []):
        label = shape.get("label", "").strip()
        if label not in label_to_id:
            print(f"  [WARN] {json_path}: 未知标签 '{label}'，跳过")
            continue

        class_id = label_to_id[label]
        shape_type = shape.get("shape_type", "")
        points = shape.get("points", [])

        if not points:
            continue

        try:
            if shape_type in {"rectangle", "polygon", "oriented_rectangle"}:
                cx, cy, w, h = points_to_bbox(points)
            elif shape_type == "circle":
                # 圆形: points 为 [center, edge_point]
                center = np.array(points[0], dtype=np.float32)
                edge = np.array(points[1], dtype=np.float32)
                r = np.linalg.norm(edge - center)
                cx, cy = center
                w = h = 2.0 * r
            else:
                print(f"  [WARN] {json_path}: 不支持的 shape_type '{shape_type}'，跳过")
                continue
        except Exception as e:
            print(f"  [WARN] {json_path}: 解析失败 - {e}")
            continue

        # 归一化
        cx /= img_w
        cy /= img_h
        w /= img_w
        h /= img_h

        # 裁剪到 [0, 1]
        cx = max(0.0, min(1.0, cx))
        cy = max(0.0, min(1.0, cy))
        w = max(0.0, min(1.0, w))
        h = max(0.0, min(1.0, h))

        if w <= 0.0 or h <= 0.0:
            continue

        lines.append(f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

    return lines


def find_image_for_json(json_path, image_dir, extensions=None):
    """
    根据 JSON 文件名查找对应的图片。
    策略:
      1. 同名不同后缀（如 a.json → a.jpg/png/bmp）
      2. JSON 中记录的 imagePath
    """
    if extensions is None:
        extensions = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"]

    base = json_path.stem

    # 策略1: 同名
    for ext in extensions:
        candidate = image_dir / (base + ext)
        if candidate.exists():
            return candidate

    # 策略2: imagePath
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        image_path = data.get("imagePath", "")
        if image_path:
            candidate = image_dir / Path(image_path).name
            if candidate.exists():
                return candidate
            # 也尝试直接用 imagePath
            candidate = Path(image_path)
            if candidate.exists():
                return candidate
    except Exception:
        pass

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Labelme JSON 标注 → YOLO txt 格式转换"
    )
    parser.add_argument(
        "--json-dir", required=True, help="labelme JSON 标注文件目录"
    )
    parser.add_argument(
        "--image-dir", required=True, help="原始图片目录（用于复制和尺寸获取）"
    )
    parser.add_argument(
        "--out-dir", required=True, help="输出 YOLO 数据集根目录"
    )
    parser.add_argument(
        "--labels", required=True, help="标签列表，逗号分隔，如 'drone' 或 'drone,ball'"
    )
    parser.add_argument(
        "--copy-images", action="store_true", default=True,
        help="同时复制图片到输出目录 (默认开启)"
    )
    parser.add_argument(
        "--no-copy-images", action="store_false", dest="copy_images",
        help="不复制图片"
    )
    args = parser.parse_args()

    json_dir = Path(args.json_dir)
    image_dir = Path(args.image_dir)
    out_dir = Path(args.out_dir)

    if not json_dir.is_dir():
        print(f"[ERROR] JSON 目录不存在: {json_dir}")
        sys.exit(1)
    if not image_dir.is_dir():
        print(f"[ERROR] 图片目录不存在: {image_dir}")
        sys.exit(1)

    labels = [l.strip() for l in args.labels.split(",") if l.strip()]
    if not labels:
        print("[ERROR] 至少需要一个标签")
        sys.exit(1)
    label_to_id = {label: idx for idx, label in enumerate(labels)}

    print(f"标签映射: {label_to_id}")

    # 创建输出目录
    out_images_dir = out_dir / "images" / "all"
    out_labels_dir = out_dir / "labels" / "all"
    out_images_dir.mkdir(parents=True, exist_ok=True)
    out_labels_dir.mkdir(parents=True, exist_ok=True)

    # 扫描 JSON 文件
    json_files = sorted(json_dir.glob("*.json"))
    if not json_files:
        print(f"[ERROR] {json_dir} 中没有找到 JSON 文件")
        sys.exit(1)

    print(f"找到 {len(json_files)} 个 JSON 标注文件")

    converted = 0
    skipped_no_image = 0
    skipped_no_shapes = 0

    for json_path in json_files:
        # 查找对应图片
        image_path = find_image_for_json(json_path, image_dir)
        if image_path is None:
            print(f"  [SKIP] {json_path.name}: 找不到对应图片")
            skipped_no_image += 1
            continue

        # 读取图片获取实际尺寸
        img = cv2.imread(str(image_path))
        if img is None:
            print(f"  [SKIP] {json_path.name}: 无法读取图片 {image_path}")
            skipped_no_image += 1
            continue
        img_h, img_w = img.shape[:2]

        # 转换
        lines = convert_json(json_path, label_to_id, img_w, img_h)
        if not lines:
            print(f"  [SKIP] {json_path.name}: 无有效标注")
            skipped_no_shapes += 1
            continue

        # 写入 YOLO txt
        txt_name = json_path.stem + ".txt"
        txt_path = out_labels_dir / txt_name
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        # 复制图片
        if args.copy_images:
            img_out = out_images_dir / image_path.name
            if not img_out.exists():
                shutil.copy2(str(image_path), str(img_out))

        converted += 1

    print(f"\n转换完成:")
    print(f"  成功: {converted}")
    print(f"  跳过(无图片): {skipped_no_image}")
    print(f"  跳过(无标注): {skipped_no_shapes}")

    # 生成 classes.txt
    classes_path = out_dir / "classes.txt"
    with open(classes_path, "w", encoding="utf-8") as f:
        for label in labels:
            f.write(label + "\n")
    print(f"  类别文件: {classes_path}")

    # 生成 dataset.yaml
    yaml_path = out_dir / "dataset.yaml"
    yaml_content = f"""# YOLO 数据集配置 (自动生成)
path: {out_dir.resolve()}
train: images/train
val: images/val

nc: {len(labels)}
names: {labels}
"""
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)
    print(f"  数据集配置: {yaml_path}")

    print(f"\n提示: 下一步划分训练集/验证集:")
    print(f"  python dataset_split.py --data-dir {out_dir} --ratio 0.8")


if __name__ == "__main__":
    main()
