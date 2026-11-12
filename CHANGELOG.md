# 更新日志 / Changelog

[中文](#中文) | [English](#english)

## 中文

主要变更按 `main` 分支提交日期记录。

### 未发布

- 将 URDF 同步工作流的 GitHub Actions 升级到 Node.js 24 兼容版本。

### 2026-11-12

#### 配置

- 示例、诊断工具和 `a1zctl serve` 读取仓库根目录的 `config.yaml`。移除 `--config` 选项。

#### 模型

- 从 `robot_descriptions` 更新 Flange 和 G1Z URDF，记录上游提交，并添加定时同步工作流。
- G1Z 动力学和运动学默认将两根手指关节固定在 URDF 零位，保留夹爪质量和惯量，继续使用六轴机械臂输入。
- 上游 G1Z 的质量和惯量参数有更新，重力补偿计算结果会随之变化。

#### 工具与文档

- `motor_diag.py --monitor` 默认按约 10 Hz 刷新状态显示。
- 将 `a1zctl` 和 CAN 命令帧间隔的详细说明移至 SDK 指南。

### 2026-11-11

#### 配置与文档

- 将 `a1z.yaml` 和 `a1z_g1z.yaml` 合并为 `config.yaml`，使用 `with_gripper` 选择夹爪配置。
- 将示教回放、夹爪用法和 API 参考移至 [SDK 指南](docs/sdk-guide.md#zh)，将 CAN 排障移至[独立文档](docs/can-troubleshooting.md#can-通信故障排查)。
- 更新产品图片并统一使用 Galaxea USB2CANFD 适配器名称。

### 2026-10-16

#### 跨平台与控制

- 合并 macOS、Windows 和 Linux 的 CAN 后端支持，以及可选 G1Z 夹爪控制。
- 合并启动反馈探测、运行时故障状态、CAN 命令帧间隔及关节限位处理。

## English

Major changes are grouped by the date they were committed to `main`.

### Unreleased

- Update the URDF synchronization actions to versions compatible with Node.js 24.

### 2026-11-12

#### Configuration

- Examples, diagnostic tools, and `a1zctl serve` read `config.yaml` from the repository root. The `--config` option has been removed.

#### Models

- Update the Flange and G1Z URDFs from `robot_descriptions`, record the upstream revision, and add a scheduled synchronization workflow.
- G1Z dynamics and kinematics lock the finger joints at the URDF zero positions by default, preserving their mass and inertia while accepting six arm joints.
- The upstream G1Z mass and inertia parameters changed, affecting computed gravity compensation.

#### Tools and documentation

- `motor_diag.py --monitor` refreshes its status display at approximately 10 Hz by default.
- Move detailed `a1zctl` and CAN command pacing instructions to the SDK guide.

### 2026-11-11

#### Configuration and documentation

- Merge `a1z.yaml` and `a1z_g1z.yaml` into `config.yaml`, using `with_gripper` to select the gripper configuration.
- Move teaching, gripper usage, and the API reference to the [SDK guide](docs/sdk-guide.md#en), and CAN troubleshooting to a [separate guide](docs/can-troubleshooting.md#can-communication-troubleshooting).
- Update the product image and use the Galaxea USB2CANFD adapter name.

### 2026-10-16

#### Cross-platform support and control

- Integrate CAN backend support for macOS, Windows, and Linux, with optional G1Z gripper control.
- Integrate startup feedback probing, runtime fault states, CAN command pacing, and joint-limit handling.
