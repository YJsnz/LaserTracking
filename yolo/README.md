# YOLOv11 目标检测 —— 训练工作流

与项目 `TRTInferX` 推理引擎同架构的 YOLOv11 模型训练流程。

## 目录结构

```
yolo/
├── README.md                       # 本文件
├── config/
│   └── train.yaml                  # (可选) 训练超参覆盖
├── scripts/
│   ├── video_to_dataset.py         # ① 视频 → 图片帧
│   ├── labelme_to_yolo.py          # ② Labelme JSON → YOLO txt
│   ├── dataset_split.py            # ③ 划分 train/val
│   ├── train.py                    # ④ 训练 YOLOv11
│   └── export.py                   # ⑤ pt → ONNX
├── datasets/
│   ├── raw_frames/                 # ① 输出的原始帧
│   ├── annotations/                # ② labelme JSON 标注文件
│   └── yolo_dataset/               # ③ YOLO 格式数据集
│       ├── images/all/             #   全部图片
│       ├── images/train/           #   训练集图片
│       ├── images/val/             #   验证集图片
│       ├── labels/all/             #   全部标注
│       ├── labels/train/           #   训练集标注
│       ├── labels/val/             #   验证集标注
│       ├── classes.txt             #   类别列表
│       └── dataset.yaml            #   YOLO 数据集配置
└── runs/train/                     # 训练输出（自动生成）
```

## 完整流程

### ① 视频切割 → 图片帧

```bash
cd yolo/scripts

# 每 5 帧取一帧，缩放到 1280x1280
python video_to_dataset.py \
    --video /path/to/your_video.mp4 \
    --out ../datasets/raw_frames \
    --interval 5 \
    --prefix drone \
    --resize 1280x1280

# 或者每秒取 2 帧
python video_to_dataset.py \
    --video /path/to/your_video.mp4 \
    --out ../datasets/raw_frames \
    --fps 2 \
    --prefix drone

# 更多选项
python video_to_dataset.py --help
```

**参数说明：**
- `--video`: 输入视频路径
- `--out`: 输出图片目录
- `--interval N`: 每隔 N 帧取一帧
- `--fps N`: 每秒取 N 帧（优先于 interval）
- `--prefix`: 文件名前缀
- `--resize WxH`: 统一缩放尺寸
- `--start N`: 从第 N 秒开始
- `--duration N`: 截取 N 秒
- `--max-frames N`: 最大导出帧数

### ② Labelme 标注

```bash
# 安装 labelme
pip install labelme

# 启动标注
labelme ../datasets/raw_frames \
    --labels drone \
    --nodata \
    --autosave \
    --output ../datasets/annotations
```

**标注要点：**
- 用**矩形框** (rectangle) 或**多边形** (polygon) 框出目标
- 标签名要与训练脚本中的一致
- 将 JSON 文件保存到 `datasets/annotations/`
- 标注完一个按 `D` 下一张，`Ctrl+S` 保存

### ③ Labelme → YOLO 格式转换

```bash
python labelme_to_yolo.py \
    --json-dir ../datasets/annotations \
    --image-dir ../datasets/raw_frames \
    --out-dir ../datasets/yolo_dataset \
    --labels drone
```

**输出：**
- `images/all/*.jpg` — 所有图片
- `labels/all/*.txt` — YOLO 格式标注 (class_id cx cy w h)
- `classes.txt` — 类别映射
- `dataset.yaml` — 数据集配置文件

### ④ 划分训练集/验证集

```bash
python dataset_split.py \
    --data-dir ../datasets/yolo_dataset \
    --ratio 0.8
```

会自动将数据按 8:2 划分为 train/val，并更新 `dataset.yaml`。

### ⑤ 训练 YOLOv11

```bash
# 安装依赖
pip install ultralytics

# 训练（推荐使用项目同款 1280x1280 输入）
python train.py \
    --data ../datasets/yolo_dataset/dataset.yaml \
    --epochs 100 \
    --imgsz 1280 \
    --batch 8

# 从本地预训练权重开始
python train.py \
    --data ../datasets/yolo_dataset/dataset.yaml \
    --weights yolo11n.pt \
    --epochs 100 \
    --imgsz 1280

# 小显存 (6GB)
python train.py \
    --data ../datasets/yolo_dataset/dataset.yaml \
    --imgsz 640 \
    --batch 4 \
    --epochs 100
```

**关键参数：**
- `--weights yolo11n.pt`: YOLOv11 nano（推荐，与项目推理引擎兼容）
- `--imgsz 1280`: 与项目 TRT engine 输入一致
- `--batch 8`: 根据 GPU 显存调整（3060 12GB 可用 batch=8 @1280）
- `--epochs 100`: 训练轮数，小数据集可设 100-200
- `--device cpu`: 无 GPU 时用 CPU 训练（很慢）

**模型尺寸选择：**

| 模型 | 参数量 | 速度 (GPU) | 适用场景 |
|------|--------|-----------|---------|
| yolo11n | 2.6M | 最快 | 嵌入式/实时 |
| yolo11s | 9.4M | 快 | 平衡 |
| yolo11m | 20.1M | 中等 | 精度优先 |
| yolo11l | 25.3M | 较慢 | 高精度 |
| yolo11x | 56.9M | 最慢 | 极致精度 |

实际部署建议从 `yolo11n` 开始。

### ⑥ 导出 ONNX → TensorRT Engine

训练完成后，使用项目自带的 TRTInferX 脚本：

```bash
# 导出 ONNX
python export.py \
    --weights ../runs/train/drone_detector/weights/best.pt \
    --imgsz 1280

# 或直接用 ultralytics 导出
yolo export model=../runs/train/drone_detector/weights/best.pt \
    format=onnx imgsz=1280 nms=True

# 构建 TensorRT FP16 engine
cd ../../src/detector/TRTInferX/scripts
PYTHON_BIN=$(which python) ./export_fp16_engine.sh \
    --pt ../../../../yolo/runs/train/drone_detector/weights/best.pt \
    --out-dir ../../model \
    --imgsz 1280 \
    --batch 1

# 将生成的 engine 放到 model 目录
cp ../../model/best_fp16.engine ../../model/
```

### ⑦ 部署到 LaserTracking 系统

```bash
# 更新 TRT 配置中的 engine 路径
# src/detector/trt_engine/config/trt.yaml 中修改:
#   engine_path: "../../model/best_fp16.engine"
#   target_w: 1280
#   target_h: 1280

# 运行系统
cd ../../src/build_full_auto/control
./control_system_demo \
    --camera-config ../../hik_camera/config/config.yaml \
    --detector-config ../../detector/config/detector.yaml \
    --control-config ../../control/config/control.yaml \
    --port /dev/ttyACM0
```

## 训练建议

1. **数据量**：至少 200+ 张标注图片（越多越好），覆盖各种角度、光照、距离
2. **标注质量**：框要紧贴目标，不要留太多边距
3. **数据多样性**：拍摄场景要包含不同背景、光照条件
4. **输入尺寸**：与部署时一致，项目用 1280x1280
5. **验证集**：验证集图片不要出现在训练集中
6. **过拟合**：小数据集可以减少 epochs 或增大 augmentation

## 常见问题

- **显存不足 (OOM)**：减小 `--batch` 或 `--imgsz`
- **labelme JSON 无对应图片**：确保图片和 JSON 在同一目录或使用 `--image-dir` 指定
- **训练 loss 不下降**：检查标注是否正确、标签名是否匹配
- **Engine 加载失败**：确保构建 engine 和运行时使用同一版本 TensorRT
