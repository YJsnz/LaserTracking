#!/usr/bin/env python3
"""
YOLOv11 训练脚本 —— 与项目推理引擎同架构。

用法:
  # 基础训练
  python train.py --data ../datasets/yolo_dataset/dataset.yaml \
      --epochs 100 --imgsz 1280 --batch 8

  # 从预训练权重开始
  python train.py --data ../datasets/yolo_dataset/dataset.yaml \
      --weights yolo11n.pt --epochs 100 --imgsz 1280

  # 自定义输出目录
  python train.py --data ../datasets/yolo_dataset/dataset.yaml \
      --name my_drone_model --epochs 200

说明:
  - 模型: YOLOv11n (nano)，与项目推理引擎同架构
  - 可选: yolov11n/s/m/l/x (n 最小最快)
  - 训练结果保存在 ../runs/train/<name>/
  - 最佳权重: ../runs/train/<name>/weights/best.pt
"""

import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="YOLOv11 训练")
    parser.add_argument(
        "--data", required=True, help="dataset.yaml 路径"
    )
    parser.add_argument(
        "--weights", default="yolo11n.pt",
        help="初始权重 (默认: yolo11n.pt, 自动下载)"
    )
    parser.add_argument(
        "--epochs", type=int, default=100, help="训练轮次 (默认: 100)"
    )
    parser.add_argument(
        "--imgsz", type=int, default=1280, help="输入尺寸 (默认: 1280)"
    )
    parser.add_argument(
        "--batch", type=int, default=8, help="batch size (默认: 8, 根据显存调整)"
    )
    parser.add_argument(
        "--name", default="drone_detector", help="实验名称"
    )
    parser.add_argument(
        "--project", default=None, help="项目输出根目录 (默认: yolo/runs/train)"
    )
    parser.add_argument(
        "--device", default="0", help="GPU 设备 (默认: 0, cpu 用于 CPU)"
    )
    parser.add_argument(
        "--workers", type=int, default=4, help="数据加载线程数"
    )
    parser.add_argument(
        "--lr0", type=float, default=0.01, help="初始学习率"
    )
    parser.add_argument(
        "--lrf", type=float, default=0.01, help="最终学习率因子 (lr0 * lrf)"
    )
    parser.add_argument(
        "--optimizer", default="auto",
        choices=["SGD", "Adam", "AdamW", "NAdam", "RAdam", "RMSProp", "auto"],
        help="优化器 (默认: auto)"
    )
    parser.add_argument(
        "--close-mosaic", type=int, default=10,
        help="最后 N 轮关闭 mosaic 增强 (默认: 10)"
    )
    parser.add_argument(
        "--resume", action="store_true", help="从上次 checkpoint 恢复训练"
    )
    parser.add_argument(
        "--cos-lr", action="store_true", default=True, help="余弦学习率调度 (默认: 开启)"
    )
    parser.add_argument(
        "--patience", type=int, default=50,
        help="早停 patience (默认: 50, 0=关闭)"
    )
    args = parser.parse_args()

    # 检查 ultralytics
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] 请先安装 ultralytics:")
        print("  pip install ultralytics")
        sys.exit(1)

    if not os.path.isfile(args.data):
        print(f"[ERROR] dataset.yaml 不存在: {args.data}")
        sys.exit(1)

    # 默认 project 目录
    if args.project is None:
        script_dir = Path(__file__).resolve().parent
        args.project = str(script_dir.parent / "runs" / "train")

    print("=" * 60)
    print("YOLOv11 训练配置")
    print("=" * 60)
    print(f"  数据: {args.data}")
    print(f"  初始权重: {args.weights}")
    print(f"  模型: YOLOv11 (同项目 TRTInferX 推理架构)")
    print(f"  输入尺寸: {args.imgsz}x{args.imgsz}")
    print(f"  Batch: {args.batch}")
    print(f"  Epochs: {args.epochs}")
    print(f"  设备: {args.device}")
    print(f"  学习率: {args.lr0} (final: {args.lr0 * args.lrf:.5f})")
    print(f"  输出: {args.project}/{args.name}")
    print("=" * 60)

    # 加载模型
    if os.path.isfile(args.weights):
        print(f"\n从本地权重加载: {args.weights}")
        model = YOLO(args.weights)
    else:
        print(f"\n从 Ultralytics 下载预训练权重: {args.weights}")
        model = YOLO(args.weights)

    # 训练
    results = model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        name=args.name,
        project=args.project,
        device=args.device,
        workers=args.workers,
        lr0=args.lr0,
        lrf=args.lrf,
        optimizer=args.optimizer,
        cos_lr=args.cos_lr,
        close_mosaic=args.close_mosaic,
        patience=args.patience,
        resume=args.resume,
        # 单类别关键参数
        single_cls=False,
        # 验证
        val=True,
        # 保存
        save=True,
        save_period=-1,  # 只保存 best 和 last
        # 详细输出
        verbose=True,
    )

    # 输出最终结果
    best_pt = Path(args.project) / args.name / "weights" / "best.pt"
    print(f"\n训练完成! 最佳权重: {best_pt}")
    print(f"\n提示: 下一步导出 ONNX → TensorRT Engine:")
    print(f"  # 1. 导出 ONNX (带 NMS, 用于 FP16 engine)")
    print(f"  python export.py --weights {best_pt} --imgsz {args.imgsz} --nms")
    print(f"\n  # 2. 构建 TensorRT engine (使用项目脚本)")
    print(f"  cd ../../src/detector/TRTInferX/scripts")
    print(f"  PYTHON_BIN=$(which python) ./export_fp16_engine.sh \\")
    print(f"      --pt {best_pt} \\")
    print(f"      --out-dir ../../model \\")
    print(f"      --imgsz {args.imgsz} \\")
    print(f"      --batch 1")


if __name__ == "__main__":
    main()
