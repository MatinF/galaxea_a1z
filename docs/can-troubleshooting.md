[中文](#can-通信故障排查) | [English](#can-communication-troubleshooting)

# CAN 通信故障排查

先根据失败阶段定位，不要把所有问题都归因于 Zadig 或内核驱动：

| 失败阶段 | 优先检查 |
|----------|----------|
| macOS 报 `usb.core.NoBackendError` | 确认使用当前 SDK 的 `verify_can_mac.sh`，并重新安装 `.[gs_usb]`；SDK 会显式加载 `libusb-package` 内置 dylib，通常无需 Homebrew libusb |
| 找不到 USB 设备 | 适配器供电、USB 线缆/接口、VID:PID；Windows 先检查设备管理器中的当前驱动，不兼容时再考虑 Zadig/WinUSB |
| 无法打开 CAN 总线 | 适配器型号、gs_usb/SocketCAN 后端、波特率、设备是否被其他程序占用 |
| 适配器可发送，但电机扫描无响应 | 机械臂上电、CANH/CANL 接线、120 Ω 终端电阻、1 Mbps 波特率、电机 ID/固件模式 |
| 电机有反馈，但控制不稳定 | 回显帧过滤、控制频率、丢帧/延迟、错误码、供电和机械负载 |

### 1. 先做不使能电机的环境和适配器检查

```bash
python --version
python -m pip --version
python -c "import pinocchio, can; print('Python environment OK')"
python tools/motor_diag.py --check-can
```

Windows 可另行运行 `python tools\verify_can_win.py`。该脚本只验证适配器识别、打开和发送，不会验证电机反馈或控制稳定性。

在 Windows 上，如果验证脚本找不到适配器或报权限错误，先在设备管理器中确认 Galaxea USB2CANFD 适配器及其驱动。驱动不兼容时再考虑用 Zadig 绑定 WinUSB。更换前记录原驱动。

### 2. 检查硬件接线

- CAN 盒（USB-CANFD 适配器）已插入电脑并牢固接触
- CAN 总线两端接线正确、无松动
- 机械臂电源已上电
- CAN 盒的终端电阻正确安装（参见 [CAN 总线配置](../README.md#配置-can-总线socketcan-模式)）

### 3. Linux：检查内核版本并修复

仅当 Linux SocketCAN 路径在完成上述检查后仍无法通信时，再排查内核 `gs_usb` 兼容性。

如果已加载 `gs_usb`、插入 Galaxea USB2CANFD 适配器后仍未出现 CAN 接口，可以手动注册该设备的 USB ID。

```bash
sudo sh -c 'echo "a8fa 8598" > /sys/bus/usb/drivers/gs_usb/new_id' 2>/dev/null || true
ip link show type can
```

查看当前内核版本：

```bash
uname -r
```

- **方案 A**：升级 Linux 内核到 **6.8.0-124** 或更新版本（如果您有其他工作依赖当前内核，建议按照方案 B 操作）
- **方案 B**：按官方文档给内核 / 驱动打补丁 —— 详见 [Galaxea 内核补丁指引](https://galaxea-ai.feishu.cn/docx/XF2ed4pmhoervNxODlfc11Gvnbb?from=from_copylink)

### 4. Linux：手动确认是否为内核兼容问题（可选）

如果不确定问题是否出在内核，或按上一步升级 / 打补丁后仍无法通信，可以手动向 J6 电机发送 CAN 指令来复现。

打开两个终端：**终端 A** 用 `candump can0` 监听总线收发；**终端 B** 依次向 J6 电机发送使能 / 运动 / 失能指令，观察终端 A 是否有反馈帧、J6 是否实际转动。

终端 A：

```bash
candump can0
```

终端 B：

```bash
# 1. 使能 J6
cansend can0 006#FFFFFFFFFFFFFFFC

# 2. 正向低速 0.5 rad/s
cansend can0 006#8000844000199800

# 3. 反向低速 -0.5 rad/s
cansend can0 006#80007BB000199800

# 4. 失能 J6
cansend can0 006#FFFFFFFFFFFFFFFD
```

预期表现：使能命令下发后，J6 应有反馈帧回到 `candump`；正 / 反向运动命令下发后，J6 应实际低速转动。

**判断依据**：如果使能命令完全没有反馈，关闭机械臂电源后重新上电 —— 若上电瞬间可以看到大约 **2 帧 CAN 数据**返回（电机上电反馈），但之后发送使能命令仍无回帧，可进一步排查内核与 SocketCAN 兼容性，参考第 3 步的方案 A 或 B。

# CAN Communication Troubleshooting

Start by identifying the stage that fails. Do not attribute every failure to Zadig or a kernel driver:

| Failure stage | Check first |
|---------------|-------------|
| macOS reports `usb.core.NoBackendError` | Use the current SDK's `verify_can_mac.sh` and reinstall `.[gs_usb]`; the SDK explicitly loads the dylib bundled by `libusb-package`, so Homebrew libusb is normally unnecessary |
| USB device not found | Adapter power, USB cable/port, and VID:PID; on Windows, inspect the current Device Manager driver before considering Zadig/WinUSB |
| CAN bus cannot be opened | Adapter model, gs_usb/SocketCAN backend, bitrate, and whether another process owns the device |
| Adapter can send, but motor scan gets no response | Arm power, CANH/CANL wiring, 120 Ω termination, 1 Mbps bitrate, motor IDs, and firmware mode |
| Motors reply, but control is unstable | Echo filtering, control frequency, loss/latency, error codes, power supply, and mechanical load |

### 1. Run environment and adapter checks that do not enable motors

```bash
python --version
python -m pip --version
python -c "import pinocchio, can; print('Python environment OK')"
python tools/motor_diag.py --check-can
```

On Windows, also run `python tools\verify_can_win.py`. It checks only adapter discovery, opening, and send submission; it does not verify motor feedback or control-loop stability.

On Windows, check the Galaxea USB2CANFD adapter and its current driver in Device Manager if the check reports a missing device or permission error. Use Zadig to bind WinUSB if the existing driver is incompatible. Record the original driver before changing it.

### 2. Check the wiring

- The USB-CANFD adapter is plugged in and seated firmly
- Both ends of the CAN bus are wired correctly and not loose
- The arm is powered on
- The CAN termination resistor is installed correctly (see [CAN bus setup](../README.md#configure-the-can-bus-socketcan))

### 3. Linux: check the kernel version and fix

Investigate kernel `gs_usb` compatibility only when the Linux SocketCAN path still fails after the checks above.

If no CAN interface appears after loading `gs_usb` and connecting the Galaxea USB2CANFD adapter, register its USB ID manually.

```bash
sudo sh -c 'echo "a8fa 8598" > /sys/bus/usb/drivers/gs_usb/new_id' 2>/dev/null || true
ip link show type can
```

Check your current kernel version:

```bash
uname -r
```

- **Option A**: upgrade the Linux kernel to **6.8.0-124** or newer (if you have other work that depends on the current kernel, prefer Option B)
- **Option B**: patch the kernel / driver as described in the [Galaxea kernel patch guide](https://galaxea-ai.feishu.cn/docx/XF2ed4pmhoervNxODlfc11Gvnbb?from=from_copylink)

### 4. Linux: manually confirm the kernel compatibility issue (optional)

If you are not sure the kernel is the culprit, or CAN still does not work after step 3, manually reproduce the issue by sending CAN commands to the J6 motor.

Open two terminals. **Terminal A** monitors bus traffic with `candump can0`; **Terminal B** sends the enable / motion / disable commands to J6 in sequence. Watch Terminal A for feedback frames and check whether J6 actually rotates.

Terminal A:

```bash
candump can0
```

Terminal B:

```bash
# 1. Enable J6
cansend can0 006#FFFFFFFFFFFFFFFC

# 2. Forward at 0.5 rad/s
cansend can0 006#8000844000199800

# 3. Reverse at -0.5 rad/s
cansend can0 006#80007BB000199800

# 4. Disable J6
cansend can0 006#FFFFFFFFFFFFFFFD
```

Expected behavior: after the enable command, J6 should emit a feedback frame visible in `candump`; after forward / reverse, J6 should physically rotate at low speed.

**Diagnosis**: if the enable command produces no feedback at all, power-cycle the arm — if you see roughly **2 CAN frames** returned during power-on (the motor's boot-up feedback) but the enable command still produces nothing, investigate kernel and SocketCAN compatibility. See Option A or B in step 3.
