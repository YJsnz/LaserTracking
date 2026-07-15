#!/usr/bin/env python3
"""
YOLOv11 模型导出脚本: .pt → ONNX → 准备用于 TensorRT engine 构建。

用法:
  # 导出带 NMS 的 ONNX (用于 FP16 engine)
  python export.py --weights ./best.pt --imgsz 1280 --nms

  # 导出不带 NMS 的 ONNX (用于 INT8 engine)
  python export.py --weights ./best.pt --imgsz 1280 --no-nms

  # 指定输出路径和 batch
  python export.py --weights ./best.pt --imgsz 1280 --batch 1 --out ./model/best.onnx

说明:
  - 导出后，使用 TRTInferX/scripts/export_fp16_engine.sh 构建 TensorRT engine
  - 或直接用 trtexec 手动构建
"""

import argparse
import os
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="YOLOv11 ONNX 导出"
    )
    parser.add_argument("--weights", required=True, help="best.pt 路径")
    parser.add_argument("--imgsz", type=int, default=1280, help="输入尺寸")
    parser.add_argument("--batch", type=int, default=1, help="Batch size")
    parser.add_argument("--nms", action="store_true", default=True,
                       help="导出时包含 NMS (默认)")
    parser.add_argument("--no-nms", action="store_false", dest="nms",
                       help="导出时不包含 NMS (raw 输出)")
    parser.add_argument("--dynamic", action="store_true", default=True,
                       help="导出动态 batch ONNX (默认)")
    parser.add_argument("--out", default=None, help="输出 ONNX 路径")
    parser.add_argument("--opset", type=int, default=17, help="ONNX opset")
    parser.add_argument("--half", action="store_true",
                       help="导出 FP16 ONNX (默认 FP32)")
    parser.add_argument("--simplify", action="store_true", default=True,
                       help="简化 ONNX 图 (默认)")
    args = parser.parse_args()

    if not os.path.isfile(args.weights):
        print(f"[ERROR] 权重文件不存在: {args.weights}")
        sys.exit(1)

    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] 请先安装 ultralytics: pip install ultralytics")
        sys.exit(1)

    # 默认输出路径
    if args.out is None:
        weights_path = Path(args.weights)
        out_dir = weights_path.parent.parent / "exports"
        out_dir.mkdir(parents=True, exist_ok=True)
        suffix = ".onnx"
        args.out = str(out_dir / (weights_path.stem + suffix))

    print("=" * 60)
    print("YOLOv11 ONNX 导出")
    print("=" * 60)
    print(f"  权重: {args.weights}")
    print(f"  输入尺寸: {args.imgsz}")
    print(f"  Batch: {args.batch}")
    print(f"  NMS: {args.nms}")
    print(f"  Dynamic: {args.dynamic}")
    print(f"  Half: {args.half}")
    print(f"  Simplify: {args.simplify}")
    print(f"  Opset: {args.opset}")
    print(f"  输出: {args.out}")
    print("=" * 60)

    model = YOLO(args.weights)

    # 导出
    success = model.export(
        format="onnx",
        imgsz=args.imgsz,
        batch=args.batch,
        nms=args.nms,
        dynamic=args.dynamic,
        half=args.half,
        simplify=args.simplify,
        opset=args.opset,
    )

    if success:
        print(f"\n导出成功: {args.out}")
        print(f"\n提示: 下一步构建 TensorRT engine:")
        trt_root = Path(__file__).resolve().parents[2] / "src" / "detector" / "TRTInferX"
        print(f"  cd {trt_root}/scripts")
        print(f"  PYTHON_BIN=$(which python) ./export_fp16_engine.sh \\")
        print(f"      --pt {args.weights} \\")
        print(f"      --out-dir ../../model \\")
        print(f"      --imgsz {args.imgsz} \\")
        print(f"      --batch {args.batch}")
        print()
        print(f"  或直接用 trtexec:")
        print(f"  trtexec \\")
        print(f"    --onnx={args.out} \\")
        print(f"    --saveEngine={Path(args.out).with_suffix('.engine')} \\")
        print(f"    --fp16 \\")
        print(f"    --minShapes=images:{args.batch}x3x{args.imgsz}x{args.imgsz} \\")
        print(f"    --optShapes=images:{args.batch}x3x{args.imgsz}x{args.imgsz} \\")
        print(f"    --maxShapes=images:{args.batch}x3x{args.imgsz}x{args.imgsz}")
    else:
        print("\n[ERROR] 导出失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
