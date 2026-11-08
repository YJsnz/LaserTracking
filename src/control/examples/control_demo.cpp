#include "common/time_utils.h"
#include "control/config.h"
#include "control/controller.h"

#include <algorithm>
#include <chrono>
#include <iostream>
#include <string>
#include <thread>

int main(int argc, char** argv) {
    std::string control_config = "../config/control.yaml";
    float test_u = 100.0f;
    float test_v = 100.0f;
    float state_pitch = 0.0f;
    float state_yaw = 0.0f;
    int steps = 1;
    int step_ms = 10;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--control-config" && i + 1 < argc) {
            control_config = argv[++i];
        } else if (arg == "--u" && i + 1 < argc) {
            test_u = std::stof(argv[++i]);
        } else if (arg == "--v" && i + 1 < argc) {
            test_v = std::stof(argv[++i]);
        } else if (arg == "--pitch" && i + 1 < argc) {
            state_pitch = std::stof(argv[++i]);
        } else if (arg == "--yaw" && i + 1 < argc) {
            state_yaw = std::stof(argv[++i]);
        } else if (arg == "--steps" && i + 1 < argc) {
            steps = std::max(1, std::stoi(argv[++i]));
        } else if (arg == "--step-ms" && i + 1 < argc) {
            step_ms = std::max(1, std::stoi(argv[++i]));
        }
    }

    control::ControlConfig ctrl_cfg;
    common::CameraModel cam_model;
    common::Boresight boresight;
    if (!control::loadControlConfig(control_config, &ctrl_cfg, &cam_model, &boresight)) {
        std::cerr << "Failed to load control config\n";
        return 1;
    }

    control::Controller controller(ctrl_cfg);
    common::TargetMeasurement meas;
    meas.valid = true;
    meas.timestamp = common::nowMs();
    meas.uv = cv::Point2f(test_u, test_v);
    meas.confidence = 1.0f;

    common::GimbalState state;
    state.pitch = state_pitch;
    state.yaw = state_yaw;
    state.timestamp = static_cast<uint32_t>(meas.timestamp);

    common::GimbalCommand cmd;
    for (int i = 0; i < steps; ++i) {
        meas.timestamp = common::nowMs();
        cmd = controller.update(meas, cam_model, boresight, state);
        if (i + 1 < steps) {
            std::this_thread::sleep_for(std::chrono::milliseconds(step_ms));
        }
    }
    std::cout << "CMD pitch=" << cmd.pitch << " yaw=" << cmd.yaw
              << " ts=" << cmd.timestamp << "\n";
    return 0;
}
