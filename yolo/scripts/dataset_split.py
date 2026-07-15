#!/usr/bin/env python3
"""
数据集划分 —— 将 YOLO 格式的 images/labels 按比例划分为 train/val。

用法:
  python dataset_split.py --data-dir ../datasets/yolo_dataset --ratio 0.8
  python dataset_split.py --data-dir ../datasets/yolo_dataset --train 100 --val 20
"""

import argparse
import os
import random
import shutil
import sys
from pathlib import Path


def load_classes(data_dir):
    classes_txt = data_dir / "classes.txt"
    if not classes_txt.exists():
        return []
    return [line.strip() for line in classes_txt.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def write_dataset_yaml(yaml_path, data_dir, names):
    quoted_names = ", ".join(f"'{name}'" for name in names)
    yaml_content = f"""# YOLO 数据集配置 (自动生成)
path: {data_dir.resolve()}
train: images/train
val: images/val

nc: {len(names)}
names: [{quoted_names}]
"""
    yaml_path.write_text(yaml_content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="YOLO 数据集划分 train/val")
    parser.add_argument(
        "--data-dir", required=True,
        help="YOLO 数据集根目录（包含 images/all 和 labels/all）"
    )
    parser.add_argument(
        "--ratio", type=float, default=0.8,
        help="训练集比例 (默认 0.8)"
    )
    parser.add_argument(
        "--train", type=int, default=0,
        help="训练集数量 (与 --val 一起使用，覆盖 --ratio)"
    )
    parser.add_argument(
        "--val", type=int, default=0,
        help="验证集数量 (与 --train 一起使用，覆盖 --ratio)"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="随机种子"
    )
    parser.add_argument(
        "--stratify", action="store_true",
        help="按标注类别分层采样 (未来扩展)"
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    src_images = data_dir / "images" / "all"
    src_labels = data_dir / "labels" / "all"

    if not src_images.is_dir():
        print(f"[ERROR] 图片目录不存在: {src_images}")
        sys.exit(1)
    if not src_labels.is_dir():
        print(f"[ERROR] 标注目录不存在: {src_labels}")
        sys.exit(1)

    # 收集有效的图片-标注对
    pairs = []
    for img_path in sorted(src_images.iterdir()):
        if not img_path.is_file():
            continue
        if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif"}:
            continue
        txt_name = img_path.stem + ".txt"
        txt_path = src_labels / txt_name
        if txt_path.exists():
            pairs.append((img_path, txt_path))
        else:
            print(f"  [WARN] {img_path.name} 无对应标注，跳过")

    if not pairs:
        print("[ERROR] 没有找到有效的图片-标注对")
        sys.exit(1)

    print(f"有效样本数: {len(pairs)}")

    random.seed(args.seed)
    random.shuffle(pairs)

    # 计算划分
    if args.train > 0 and args.val > 0:
        n_train = args.train
        n_val = args.val
        if n_train + n_val > len(pairs):
            print(f"[WARN] 训练+验证({n_train}+{n_val}) > 总数({len(pairs)})，调整中...")
            n_train = int(len(pairs) * args.ratio)
            n_val = len(pairs) - n_train
    else:
        n_train = int(len(pairs) * args.ratio)
        n_val = len(pairs) - n_train

    train_pairs = pairs[:n_train]
    val_pairs = pairs[n_train:n_train + n_val]

    print(f"训练集: {len(train_pairs)}")
    print(f"验证集: {len(val_pairs)}")

    # 清理目标目录
    for subset in ["train", "val"]:
        img_dir = data_dir / "images" / subset
        lbl_dir = data_dir / "labels" / subset
        if img_dir.exists():
            shutil.rmtree(img_dir)
        if lbl_dir.exists():
            shutil.rmtree(lbl_dir)
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

    def copy_subset(pairs_list, subset):
        img_dst = data_dir / "images" / subset
        lbl_dst = data_dir / "labels" / subset
        for img_path, txt_path in pairs_list:
            shutil.copy2(str(img_path), str(img_dst / img_path.name))
            shutil.copy2(str(txt_path), str(lbl_dst / txt_path.name))

    copy_subset(train_pairs, "train")
    copy_subset(val_pairs, "val")

    # 更新 dataset.yaml
    yaml_path = data_dir / "dataset.yaml"
    if yaml_path.exists():
        names = load_classes(data_dir)
        try:
            import yaml
            with open(yaml_path, "r") as f:
                cfg = yaml.safe_load(f)
            if not isinstance(cfg, dict):
                cfg = {}
            # 核心字段
            cfg["path"] = str(data_dir.resolve())
            cfg["train"] = "images/train"
            cfg["val"] = "images/val"
            # 如果没读出来，自己生成
            if "nc" not in cfg or "names" not in cfg:
                if names:
                    cfg["nc"] = len(names)
                    cfg["names"] = names
            with open(yaml_path, "w") as f:
                yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
        except ModuleNotFoundError:
            if names:
                write_dataset_yaml(yaml_path, data_dir, names)
            else:
                print("  [WARN] 未安装 PyYAML 且 classes.txt 不存在，无法更新 dataset.yaml")
        except Exception:
            if names:
                write_dataset_yaml(yaml_path, data_dir, names)
            else:
                print("  [WARN] dataset.yaml 解析失败且 classes.txt 不存在，无法更新")
        print(f"  已更新: {yaml_path}")
    else:
        names = load_classes(data_dir)
        if names:
            write_dataset_yaml(yaml_path, data_dir, names)
            print(f"  已生成: {yaml_path}")

    print(f"\n完成! 数据集路径: {data_dir}")
    print(f"  images/train/  ({len(train_pairs)} files)")
    print(f"  images/val/    ({len(val_pairs)} files)")
    print(f"  labels/train/  ({len(train_pairs)} files)")
    print(f"  labels/val/    ({len(val_pairs)} files)")
    print(f"\n提示: 下一步训练:")
    print(f"  python train.py --data {data_dir}/dataset.yaml --epochs 100 --imgsz 1280")


if __name__ == "__main__":
    main()
