#!/usr/bin/env python3
"""
视频切割脚本 —— 将视频按帧率/间隔切割为图片数据集。

用法:
  python video_to_dataset.py --video ./my_video.mp4 --out ../datasets/raw_frames \
      --interval 5 --prefix drone --resize 1280x1280
  python video_to_dataset.py --video ./my_video.mp4 --out ../datasets/raw_frames \
      --fps 2 --prefix drone

说明:
  - --interval N : 每隔 N 帧取一帧
  - --fps N      : 每秒取 N 帧（与 interval 互斥，优先使用 fps）
  - --resize WxH : 统一缩放输出尺寸（可选）
  - --start N     : 从第 N 秒开始
  - --duration N  : 截取 N 秒（从 start 开始）
"""

import argparse
import os
import sys
from pathlib import Path

import cv2


def parse_size(s: str):
    """解析 WxH 字符串，如 "1280x1280" -> (1280, 1280)。"""
    parts = s.strip().split("x")
    if len(parts) != 2:
        raise ValueError(f"Invalid size: {s}, expect WxH")
    return int(parts[0]), int(parts[1])


def main():
    parser = argparse.ArgumentParser(description="视频切割为图片数据集")
    parser.add_argument("--video", required=True, help="输入视频路径")
    parser.add_argument("--out", required=True, help="输出图片目录")
    parser.add_argument("--prefix", default="frame", help="输出文件名前缀")
    parser.add_argument(
        "--interval", type=int, default=0, help="每隔 N 帧取一帧（默认0，由 --fps 决定）"
    )
    parser.add_argument("--fps", type=float, default=0, help="每秒取样帧数（优先于 --interval）")
    parser.add_argument("--start", type=float, default=0, help="起始秒数")
    parser.add_argument("--duration", type=float, default=0, help="截取时长（秒），0=到结尾")
    parser.add_argument("--resize", type=str, default="", help="输出尺寸 WxH，如 1280x1280")
    parser.add_argument("--max-frames", type=int, default=0, help="最大导出帧数（0=不限制）")
    args = parser.parse_args()

    if not os.path.isfile(args.video):
        print(f"[ERROR] 视频文件不存在: {args.video}")
        sys.exit(1)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"[ERROR] 无法打开视频: {args.video}")
        sys.exit(1)

    src_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    print(f"视频信息:")
    print(f"  文件: {args.video}")
    print(f"  分辨率: {int(width)}x{int(height)}")
    print(f"  FPS: {src_fps:.2f}")
    print(f"  总帧数: {int(total_frames)}")
    if total_frames > 0 and src_fps > 0:
        print(f"  时长: {total_frames / src_fps:.1f}s")

    # 计算间隔
    if args.fps > 0:
        interval = max(1, int(round(src_fps / args.fps)))
        print(f"  采样: 每秒 {args.fps} 帧 → 间隔 {interval} 帧")
    elif args.interval > 0:
        interval = args.interval
        print(f"  采样: 每 {interval} 帧")
    else:
        interval = max(1, int(round(src_fps)))  # 默认每秒一帧
        print(f"  采样: 默认每秒1帧 → 间隔 {interval} 帧")

    # 跳转到起始秒
    if args.start > 0:
        start_frame = int(args.start * src_fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        print(f"  起始: {args.start}s (帧 {start_frame})")

    # 结束帧
    end_frame = float("inf")
    if args.duration > 0:
        end_frame = (args.start + args.duration) * src_fps
        print(f"  结束: {args.start + args.duration}s")

    resize = parse_size(args.resize) if args.resize else None

    frame_idx = 0
    saved = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
        if current_frame >= end_frame:
            break

        if frame_idx % interval == 0:
            if resize is not None:
                frame = cv2.resize(frame, resize, interpolation=cv2.INTER_AREA)

            fname = out_dir / f"{args.prefix}_{saved:06d}.jpg"
            cv2.imwrite(str(fname), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            saved += 1

            if saved % 50 == 0:
                print(f"  已导出 {saved} 张...")

            if args.max_frames > 0 and saved >= args.max_frames:
                print(f"  达到最大导出帧数 {args.max_frames}，停止")
                break

        frame_idx += 1

    cap.release()
    print(f"\n完成! 共导出 {saved} 张图片 → {out_dir}")
    print(f"提示: 下一步使用 labelme 标注这些图片:")
    print(f"  labelme {out_dir} --labels drone --nodata")


if __name__ == "__main__":
    main()
