# A1Z SDK Guide

[中文](#zh) | [English](#en)

<a id="zh"></a>

## 中文

首次运行实机示例前，请阅读 [快速开始](../README.md#快速开始)和[安全注意事项](../README.md#安全注意事项)。命令从仓库根目录运行。

### 零力示教与回放

`teach_and_play.py` 分为两个子命令：`record`（录制）和 `play`（回放）。

#### 录制轨迹

```bash
# 录制并保存到文件（默认 can0，50 Hz 采样）
python examples/teach_and_play.py record teach.json

# 指定 CAN 口和采样频率
python examples/teach_and_play.py --can can1 record teach.json --sample-hz 100
```

启动后机械臂进入零力漂浮模式，可自由拖拽：

```
[record] Arm running in zero-gravity mode.
[record] Press ENTER to START recording...   ← 按 Enter 开始录制
[record] Recording — move the arm freely.  Press ENTER to STOP.
                                             ← 拖动到目标轨迹后按 Enter 停止
[record] Recorded 243 frames (4.86s).
[record] Saved to teach.json
```

录制完成后机械臂自动回零位再失能。Ctrl+C 可随时中止（同样会回零再失能）。

#### 回放轨迹

```bash
# 以原速回放
python examples/teach_and_play.py play teach.json

# 0.5 倍速回放
python examples/teach_and_play.py play teach.json --speed 0.5

# 循环回放直到 Ctrl+C
python examples/teach_and_play.py play teach.json --loop

# 指定 CAN 口
python examples/teach_and_play.py --can can1 play teach.json
```

启动后机械臂先运动到轨迹起点，按 Enter 开始回放：

```
[play] Loaded 243 frames (4.86s).
[play] Returning to start position...
[play] Ready.
[play] Press ENTER to PLAY (4.86s at 1.0x)...   ← 按 Enter 播放
[play] Playing (loop 1)...
[play] Playback complete.
```

回放结束（或 Ctrl+C 中止）后机械臂自动回零位再失能。

### 夹爪

夹爪出厂已完成零点标定，断电重启后无需归零，直接上电即可使用。

#### 命令行示例

先在 `config.yaml` 中设置 `with_gripper: true`。

```bash
# 位置保持 + 低速移动到目标（with_gripper: true，第 7 个值为夹爪开度）
python examples/position_hold.py --q_target_deg 0,30,-20,-15,0,0,0.5 --speed 0.5

# 夹爪测试（自由行程 + 力矩饱和验证）
python examples/gripper_hybrid_test.py --can can0
```

#### Python 用法

```python
from a1z.robots.get_robot import get_a1z_robot

# 创建带夹爪的机械臂
robot = get_a1z_robot(
    with_gripper=True,
    gripper_max_torque=2.0,   # 夹持力矩上限（Nm），默认 2.0 Nm
)
robot.start()   # 自动使能夹爪并归零到张开位

# 控制夹爪
robot.command_gripper(0.0)   # 关闭
robot.command_gripper(1.0)   # 张开
robot.command_gripper(0.5)   # 50% 开度

# 读取夹爪状态
norm = robot.get_gripper_pos()           # 当前指令开度
obs  = robot.get_observations()          # 包含 gripper_pos 的完整观测字典

# 同时控制关节和夹爪（7 元素数组，第 7 个为夹爪）
import numpy as np
robot.command_joint_pos(np.array([0, 0.5, -0.5, 0, 0, 0, 0.8]))
robot.move_joints(np.array([0, 0.3, -0.3, 0, 0, 0, 0.0]), speed=0.5)

robot.stop()
```

#### 力矩限制（夹持保护）

`gripper_max_torque` 通过力位混控模式的硬件电流饱和环节直接限制夹持力矩：夹爪接触物体后，电流被钳位在 `i_des = max_torque / 11.0`，力矩不再随位置误差增大，无论物体尺寸如何均不会超力。

```python
robot = get_a1z_robot(
    with_gripper=True,
    gripper_max_torque=1.0,   # 1.0 Nm 限制，适合轻物体
)
```

### API 参考

#### `get_a1z_robot()`

工厂函数，创建配置好的 ArmRobot 实例：

```python
get_a1z_robot(
    can_channel="can0",           # CAN 通道名
    gravity_comp_factor=1.0,      # 重力补偿比例 (0=关闭, 1=全补偿)
    zero_gravity_mode=True,       # True=零力漂浮, False=位置保持
    control_freq_hz=250,          # 控制回路频率 (Hz)
    urdf_path=None,               # 覆盖 URDF 路径
    default_kp=None,              # 覆盖默认位置增益
    default_kd=None,              # 覆盖默认速度增益
    with_gripper=False,           # True=启用夹爪 (CAN ID 0x07)
    gripper_max_torque=2.0,       # 夹爪最大夹持力矩 (Nm)，默认 2.0 Nm
    inter_cmd_gap_us=None,        # CAN 命令帧间隔 (µs)：None=默认 250，0=关闭，上限 500
    bustype=None,                 # CAN 后端（None=OS 默认: Linux→socketcan, macOS/Windows→gs_usb）
) -> ArmRobot
```

#### `ArmRobot` 主要方法

| 方法 | 说明 |
|------|------|
| `start(initial_kp, initial_kd)` | 使能电机，启动控制回路（含夹爪归零）；仅 `STOPPED` 状态可启动，否则抛 `RuntimeError`；硬故障后须重建对象 |
| `stop()` | 停止控制回路并失能所有电机；**不关闭 CAN 总线**（总线由对象析构或外部调用方管理） |
| `estop(reason, fault_code) -> bool` | 软急停：kp=0、kd 减半、锁定当前位置，重力补偿继续、**电机保持使能**；详见 [安全状态机](../README.md#安全状态机) |
| `release(expected_fault_code=None) -> bool` | 解除软急停/保持并恢复 `RUNNING`；要求反馈新鲜、状态匹配，失败返回 `False` 并保持现状 |
| `hold_position(reason, fault_code) -> bool` | 锁存全增益 MIT 位置保持（`FAULT_HOLD`），控制回路保持运行 |
| `hold_last_command() -> bool` | 保持最后一次已下发的位置目标并清零运动前馈（不锁存故障，用于 teleop 输入丢失） |
| `latch_last_command(reason, fault_code) -> bool` | 锁存最后一次已下发目标（`COMMAND_HOLD`），`release()` 成功前拒绝新命令 |
| `get_fault_status() -> dict` | 查询安全状态快照：`state` / `code` / `reason` / 反馈健康度 / `restart_allowed` 等 |
| `get_joint_pos() -> np.ndarray` | 获取当前关节角 (rad)；有夹爪时返回 7 元素数组（第 7 个为夹爪归一化开度） |
| `get_joint_state() -> dict` | 获取 `{pos, vel, eff}`（仅 6 轴） |
| `get_observations() -> dict` | 获取 `{joint_pos, joint_vel, joint_eff}`；带夹爪时额外包含 `gripper_pos` |
| `command_joint_pos(pos) -> bool` | 设置目标关节角（越界始终裁剪，见 [关节限位处理](../README.md#关节限位处理)）；可传 7 元素数组，第 7 个为夹爪开度 [0, 1]；急停/故障中拒绝并返回 `False` |
| `command_joint_state(joint_state) -> bool` | 设置目标关节角 + 自定义增益；vel/kp/kd/acc/torque_ff 越界则拒绝整帧并返回 `False` |
| `command_gripper(value)` | 设置夹爪目标开度 [0.0=关闭, 1.0=全开] |
| `get_gripper_pos() -> float\|None` | 获取当前夹爪指令开度；无夹爪返回 None |
| `move_joints(target, speed, kp, kd, max_jump_rad, sync_to_measured, gain_ramp_s)` | minimum-jerk 插值移动到目标位置（阻塞）；目标越界超出容差抛 `ValueError`；`max_jump_rad` 可拒绝距当前测量位置过远的目标 |
| `is_running` / `is_estopped` | 控制回路是否在运行 / 是否处于急停或故障保持（兼容属性） |

#### `Kinematics` 运动学

```python
from a1z.robots.kinematics import Kinematics

kin = Kinematics("/path/to/urdf")

# 正运动学 → 4x4 齐次变换矩阵
T = kin.fk(q)

# 逆运动学 (阻尼最小二乘)
converged, q_sol = kin.ik(target_pose, init_q=q0)
```

<a id="en"></a>

## English

Read the [quick start](../README.md#quick-start) and [safety instructions](../README.md#safety) before running hardware examples. Run the commands from the repository root.

### Zero-Force Teaching and Playback

`teach_and_play.py` has two sub-commands: `record` and `play`.

#### Record a Trajectory

```bash
# Record and save to file (default can0, 50 Hz sampling)
python examples/teach_and_play.py record teach.json

# Specify CAN channel and sample rate
python examples/teach_and_play.py --can can1 record teach.json --sample-hz 100
```

The arm enters zero-force float mode and can be freely backdriven:

```
[record] Arm running in zero-gravity mode.
[record] Press ENTER to START recording...   ← press Enter to begin
[record] Recording — move the arm freely.  Press ENTER to STOP.
                                             ← guide the arm, then press Enter
[record] Recorded 243 frames (4.86s).
[record] Saved to teach.json
```

The arm returns to zero position and disables after recording. Ctrl+C aborts safely (also returns to zero).

#### Play Back a Trajectory

```bash
# Play at original speed
python examples/teach_and_play.py play teach.json

# Play at 0.5× speed
python examples/teach_and_play.py play teach.json --speed 0.5

# Loop until Ctrl+C
python examples/teach_and_play.py play teach.json --loop

# Specify CAN channel
python examples/teach_and_play.py --can can1 play teach.json
```

The arm moves to the trajectory start position first, then waits for Enter:

```
[play] Loaded 243 frames (4.86s).
[play] Returning to start position...
[play] Ready.
[play] Press ENTER to PLAY (4.86s at 1.0x)...   ← press Enter to play
[play] Playing (loop 1)...
[play] Playback complete.
```

After playback (or Ctrl+C), the arm returns to zero and disables.

### Gripper

The gripper ships with factory zero calibration and requires no re-homing after power cycle.

#### CLI examples

Set `with_gripper: true` in `config.yaml` first.

```bash
# Position hold + move slowly to target (with_gripper: true, seventh value is gripper opening)
python examples/position_hold.py --q_target_deg 0,30,-20,-15,0,0,0.5 --speed 0.5

# Gripper test (free travel + torque saturation)
python examples/gripper_hybrid_test.py --can can0
```

#### Python usage

```python
from a1z.robots.get_robot import get_a1z_robot

robot = get_a1z_robot(
    with_gripper=True,
    gripper_max_torque=2.0,   # max gripping torque (Nm), default 2.0 Nm
)
robot.start()   # enables gripper and homes to open position

# Control the gripper
robot.command_gripper(0.0)   # close
robot.command_gripper(1.0)   # fully open
robot.command_gripper(0.5)   # 50% open

# Read gripper state
norm = robot.get_gripper_pos()           # current command position
obs  = robot.get_observations()          # full observation dict including gripper_pos

# Control arm and gripper together (7-element array, 7th = gripper)
import numpy as np
robot.command_joint_pos(np.array([0, 0.5, -0.5, 0, 0, 0, 0.8]))
robot.move_joints(np.array([0, 0.3, -0.3, 0, 0, 0, 0.0]), speed=0.5)

robot.stop()
```

#### Torque Limiting (Grasp Protection)

`gripper_max_torque` limits gripping force directly via the hardware current saturation in MIT mixed control mode. Once the gripper contacts an object, current is clamped to `i_des = max_torque / 11.0` and torque no longer grows with position error, regardless of object size.

```python
robot = get_a1z_robot(
    with_gripper=True,
    gripper_max_torque=1.0,   # 1.0 Nm, suitable for lighter objects
)
```

### API Reference

#### `get_a1z_robot()`

Factory function that creates a configured `ArmRobot` instance:

```python
get_a1z_robot(
    can_channel="can0",           # CAN channel name
    gravity_comp_factor=1.0,      # Gravity compensation scale (0=off, 1=full)
    zero_gravity_mode=True,       # True=zero-force float, False=position hold
    control_freq_hz=250,          # Control loop frequency (Hz)
    urdf_path=None,               # Override URDF path
    default_kp=None,              # Override default position gains
    default_kd=None,              # Override default velocity gains
    with_gripper=False,           # True=enable gripper (CAN ID 0x07)
    gripper_max_torque=2.0,       # Max gripping torque (Nm), default 2.0 Nm
    inter_cmd_gap_us=None,        # CAN command pacing gap (µs): None=250 default, 0=off, max 500
    bustype=None,                 # CAN backend (None=OS default: Linux→socketcan, macOS/Windows→gs_usb)
) -> ArmRobot
```

#### `ArmRobot` Key Methods

| Method | Description |
|--------|-------------|
| `start(initial_kp, initial_kd)` | Enable motors and start the control loop (gripper homing included); only allowed from `STOPPED` — otherwise raises `RuntimeError`; after a hard fault the object cannot be restarted (recreate it) |
| `stop()` | Stop the control loop and disable all motors; does **not** shut down the CAN bus (the bus is closed on object destruction or by the owning caller) |
| `estop(reason, fault_code) -> bool` | Soft emergency stop: kp=0, kd halved, position pinned to the current pose; gravity compensation keeps running and **motors stay enabled**; see [Safety State Machine](../README.md#safety-state-machine) |
| `release(expected_fault_code=None) -> bool` | Release a soft estop / hold back to `RUNNING`; requires fresh feedback and a matching state — returns `False` (and holds) otherwise |
| `hold_position(reason, fault_code) -> bool` | Latch a strict full-gain MIT position hold (`FAULT_HOLD`) while the control loop stays alive |
| `hold_last_command() -> bool` | Keep the last queued position target and clear motion feedforward (no fault latched; teleop input-loss behavior) |
| `latch_last_command(reason, fault_code) -> bool` | Latch the last transmitted target (`COMMAND_HOLD`); new commands are rejected until `release()` succeeds |
| `get_fault_status() -> dict` | Thread-safe safety snapshot: `state` / `code` / `reason` / per-joint feedback health / `restart_allowed`, etc. |
| `get_joint_pos() -> np.ndarray` | Get current joint angles (rad); returns 7-element array when gripper is attached (7th = normalized gripper position) |
| `get_joint_state() -> dict` | Get `{pos, vel, eff}` (arm joints only) |
| `get_observations() -> dict` | Get `{joint_pos, joint_vel, joint_eff}`; includes `gripper_pos` when a gripper is attached |
| `command_joint_pos(pos) -> bool` | Set target joint angles (out-of-limits targets are always clipped, see [Joint Limit Handling](../README.md#joint-limit-handling)); accepts 7-element array (7th = gripper [0, 1]); returns `False` when rejected (e.g. while estopped) |
| `command_joint_state(joint_state) -> bool` | Set target joint angles + custom gains; out-of-range vel/kp/kd/acc/torque_ff rejects the whole frame (`False`) |
| `command_gripper(value)` | Set gripper target position [0.0=closed, 1.0=fully open] |
| `get_gripper_pos() -> float\|None` | Get current gripper command position; returns None without gripper |
| `move_joints(target, speed, kp, kd, max_jump_rad, sync_to_measured, gain_ramp_s)` | Minimum-jerk interpolation to target (blocking); a target beyond the joint-limit tolerance raises `ValueError`; `max_jump_rad` rejects targets too far from the measured pose |
| `is_running` / `is_estopped` | Whether the control loop is active / whether the robot is in estop or a fault hold (compatibility properties) |

#### `Kinematics`

```python
from a1z.robots.kinematics import Kinematics

kin = Kinematics("/path/to/urdf")

# Forward kinematics → 4×4 homogeneous transform
T = kin.fk(q)

# Inverse kinematics (damped least squares)
converged, q_sol = kin.ik(target_pose, init_q=q0)
```
