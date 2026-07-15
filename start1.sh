cd /home/geqingyu/Code/LaserTracking-2026-main/src/build_full_auto/control

./control_system_demo \
  --camera-config ../../hik_camera/config/config.yaml \
  --detector-config ../../detector/config/detector.yaml \
  --control-config ../../control/config/control.yaml \
  --port none \
  --send-hz 400