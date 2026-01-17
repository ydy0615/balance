# 四足机器人控制面板（Balance）  
**基于 Gradio 的 Web UI，封装了 `BalanceController`、`LegsController` 与 IMU 驱动，实现串口自动打开、日志记录、实时电机使能/失能、PID 平衡控制、速度控制和扭矩读取。**

## 目录
- [项目简介](#项目简介)  
- [环境要求](#环境要求)  
- [快速安装](#快速安装)  
- [运行方式](#运行方式)  
- [主要功能](#主要功能)  
- [代码结构概览](#代码结构概览)  
- [使用说明](#使用说明)  
- [PID 参数调节指南](#pid-参数调节指南)  
- [常见问题与故障排查](#常见问题与故障排查)  
- [许可证](#许可证)

## 项目简介
本项目提供一个面向四足机器人的控制面板，使用 **Gradio** 构建网页 UI，能够在浏览器中直接操控机器人。核心逻辑封装在 `BalanceController`（位于 `balance.py`）中，采用 **PID 算法**进行姿态平衡控制，支持实时参数调整。

> **注意**：若硬件未连接，`BalanceController` 与 `LegsController` 会捕获异常并创建 dummy 对象，保证脚本仍可运行而不会崩溃。

## 环境要求
- **操作系统**：Linux（POSIX 串口）或 Windows（使用对应的串口驱动）  
- **Python**：>=3.8  
- **依赖库**（已在 `pyproject.toml` 中声明）  
  - `gradio<6.0`  
  - `pyserial>=3.5`  
  - `numpy<2.0`  
  - `pybind11>=2.10`（用于编译 C++ IMU 驱动）  
- **硬件**  
  - 4×腿部电机（DM4340）+ 4×轮子电机（DMH6215）  
  - IMU（通过 `dm_imu` 包的 `DmImu`）

## 快速安装
```bash
# 克隆仓库
git clone https://github.com/ydy0615/balance.git
cd balance

# 创建并激活虚拟环境（推荐）
python -m venv venv
.\venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/macOS

# 安装 Python 依赖
pip install gradio pyserial numpy pybind11

# 编译 C++ IMU 驱动（需要 cmake、gcc/clang）
cd dm_imu
mkdir build && cd build
cmake .. && cmake --build .
cd ../..
```

> 若只想运行 UI 而不编译 C++ 部分，可跳过编译步骤，`dm_imu` 包会在运行时尝试加载已编译的 `.so`/`.dll`，若不存在则使用 Python 伪实现（仅用于调试）。

## 运行方式
```bash
python main.py
```
启动后会在终端显示类似信息：
```
Running on http://0.0.0.0:7860/
```
在浏览器打开该地址即可看到 **四足机器人控制面板**。

## 主要功能
| 功能 | 对应方法 | UI 控件 | 说明 |
|------|----------|---------|------|
| 自动打开串口 | `open_port` | "🔌 打开串口" 按钮 | 实例化 `BalanceController` 并打开串口 |
| 电机使能 | `enable_all` | "✅ 使能全部" 按钮 | 使能四条腿电机 + 四个轮子电机 |
| 电机失能 | `disable_all` | "❌ 失能全部" 按钮 | 失能所有电机 |
| 启动平衡控制 | `start_balance` | "▶️ 启动平衡控制" 按钮 | 检查电机是否已使能，启动后台平衡循环 |
| **速度控制** | `update_speed` | spd/off 滑块 | 实时调整轮子速度，平衡循环自动读取 |
| **PID 参数调节** | `update_pid` / `reset_pid` | Kp/Ki/Kd 滑块 + "应用/重置" 按钮 | 实时更新 PID 控制参数 |
| 扭矩读取 | `get_torque` | "📊 读取扭矩" 按钮 | 返回四条腿的当前扭矩值（N/m） |
| 日志显示 | `refresh_log` | "刷新日志" 按钮 + 文本框 | 读取并显示 `ui.log` 内容 |

## 代码结构概览
```
balance/
│
├─ main.py               # Gradio UI 与业务入口
├─ balance.py            # BalanceController（PID平衡算法、线程管理）
├─ Legs_controller.py    # LegsController（电机底层控制）
├─ dm_imu/               # C++ IMU 驱动（pybind11 包装）
│   ├─ src/
│   │   ├─ imu_driver.cpp
│   │   └─ bsp_crc.cpp
│   └─ __init__.py
├─ pyproject.toml        # 项目元信息与依赖声明
├─ README.md             # 本文档
└─ ... (其他辅助脚本、测试文件)
```

## 使用说明
1. **检查硬件**：确保机器人电机控制板和 IMU 已正确连接，串口设备路径为 `/dev/dm-u2can` 和 `/dev/dm-imu`。  
2. **启动 UI**：运行 `python main.py`，打开浏览器访问 `http://<本机IP>:7860`。  
3. **日志查看**：点击 "刷新日志" 可实时读取 `ui.log`。  
4. **电机使能**：先点击 "✅ 使能全部"。  
5. **启动平衡**：在电机已使能后点击 "▶️ 启动平衡控制"。后台线程会不断读取 IMU 数据并根据 PID 算法调节腿部位置。  
6. **实时调参（平衡运行中）**：
   - 调整 **spd/off** 滑块：立即更新轮子速度
   - 调整 **PID 参数** 滑块：点击 "应用PID参数" 生效
7. **扭矩读取**：点击 "📊 读取扭矩" 查看四条腿当前扭矩。

## PID 参数调节指南
### 控制原理
```
u(t) = Kp × e(t) + Ki × ∫e(t)dt + Kd × de/dt)

其中：
e(t) = 目标角度(0) - 当前姿态角
Kp - 比例系数：对当前偏差的响应强度
Ki - 积分系数：消除稳态误差（长时间倾斜）
Kd - 微分系数：抑制超调和振荡
```

### 推荐调试步骤
| 步骤 | 参数设置 | 说明 |
|------|----------|------|
| 1. 粗调 Kp | Kp=0.5, Ki=0, Kd=0 | 从小到大增加，直到系统能快速响应倾斜但不剧烈振荡 |
| 2. 加入 Ki | Ki=0.01~0.05 | 消除稳态误差（机器人无法完全回中）|
| 3. 微调 Kd | Kd=0.1~0.5 | 抑制超调和高频振荡 |

### 参数范围参考
| 参数 | 推荐范围 | 说明 |
|------|----------|------|
| Kp (Pitch/Roll) | 0.01 ~ 1.0 | 太小迟钝，太大震荡 |
| Ki (Pitch/Roll) | 0.0001 ~ 0.1 | 太大导致积分饱和 |
| Kd (Pitch/Roll) | 0.001 ~ 1.0 | 太大反应迟钝 |

## 常见问题与故障排查
| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| **UI 无法打开** | 未安装 `gradio` 或端口被占用 | `pip install gradio`，或更换 `server_port` 参数 |
| **串口打开失败** | 设备路径错误、权限不足或硬件未连接 | 检查 `BalanceController.__init__` 中的 `leg_port` 与 `imu_port`，在 Linux 上使用 `sudo chmod a+rw /dev/ttyUSB*` |
| **日志不刷新** | `ui.log` 未生成或文件被锁定 | 确认 `log()` 已被调用；手动删除 `ui.log` 让程序重新创建 |
| **电机不使能** | `LegsController` 初始化异常 | 查看终端输出的 "初始化 LegsController 失败" 信息；确保 `u2can` 包已正确安装且串口可用 |
| **平衡控制未启动** | `motors_enabled` 为 `False`（未使能） | 必须先点击 "✅ 使能全部"，然后再点击 "▶️ 启动平衡控制" |
| **重复启动报错** | 主循环已在运行中 | 程序已内置防重复启动机制，无需手动停止 |
| **读取扭矩返回 "错误"** | `controller.get_legs_torque()` 抛异常 | 检查电机是否已连接，确保已使能 |
| **IMU 数据异常** | IMU 未启动或波特率不匹配 | 确认串口配置正确；若硬件缺失，程序会使用 DummyImu（返回零姿态） |

## 许可证
本项目采用 **MIT 许可证**。详情请参见根目录下的 `LICENSE` 文件。
