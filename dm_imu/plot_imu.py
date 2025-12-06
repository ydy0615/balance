#!/usr/bin/env python3
"""
绘制 dm_imu/test_imu.cpp 生成的 CSV 数据。

使用方式：
    1. 确保已安装 matplotlib（pip install matplotlib）。
    2. 运行 C++ 程序生成 imu_data.csv。
    3. 执行本脚本：
           python3 dm_imu/plot_imu.py
    4. 脚本会在同目录下生成 `imu_plot.png` 并显示图形窗口（如果有可视化环境）。
"""

import csv
import os
import sys

import matplotlib.pyplot as plt

def read_csv(csv_path):
    """读取 CSV，返回每列的数据列表。"""
    if not os.path.isfile(csv_path):
        print(f"错误：未找到 CSV 文件 {csv_path}", file=sys.stderr)
        sys.exit(1)

    indices = []
    roll = []
    pitch = []
    yaw = []
    accx = []
    accy = []
    accz = []
    gyrox = []
    gyroy = []
    gyroz = []

    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            indices.append(int(row['index']))
            roll.append(float(row['roll']))
            pitch.append(float(row['pitch']))
            yaw.append(float(row['yaw']))
            accx.append(float(row['accx']))
            accy.append(float(row['accy']))
            accz.append(float(row['accz']))
            gyrox.append(float(row['gyrox']))
            gyroy.append(float(row['gyroy']))
            gyroz.append(float(row['gyroz']))

    return {
        'index': indices,
        'roll': roll,
        'pitch': pitch,
        'yaw': yaw,
        'accx': accx,
        'accy': accy,
        'accz': accz,
        'gyrox': gyrox,
        'gyroy': gyroy,
        'gyroz': gyroz,
    }

def plot_data(data, out_path):
    """绘制三组曲线（姿态、加速度、陀螺仪）并保存为 PNG。"""
    idx = data['index']

    plt.figure(figsize=(12, 9))

    # 1. 姿态（Roll, Pitch, Yaw）
    ax1 = plt.subplot(3, 1, 1)
    ax1.plot(idx, data['roll'], label='Roll')
    ax1.plot(idx, data['pitch'], label='Pitch')
    ax1.plot(idx, data['yaw'], label='Yaw')
    ax1.set_ylabel('Angle (°)')
    ax1.set_title('IMU 姿态')
    ax1.legend()
    ax1.grid(True)

    # 2. 加速度（X, Y, Z）
    ax2 = plt.subplot(3, 1, 2)
    ax2.plot(idx, data['accx'], label='Acc X')
    ax2.plot(idx, data['accy'], label='Acc Y')
    ax2.plot(idx, data['accz'], label='Acc Z')
    ax2.set_ylabel('Acceleration (g)')
    ax2.set_title('加速度')
    ax2.legend()
    ax2.grid(True)

    # 3. 陀螺仪（X, Y, Z）
    ax3 = plt.subplot(3, 1, 3)
    ax3.plot(idx, data['gyrox'], label='Gyro X')
    ax3.plot(idx, data['gyroy'], label='Gyro Y')
    ax3.plot(idx, data['gyroz'], label='Gyro Z')
    ax3.set_xlabel('Sample Index')
    ax3.set_ylabel('Angular Velocity (°/s)')
    ax3.set_title('陀螺仪')
    ax3.legend()
    ax3.grid(True)

    plt.tight_layout()
    plt.savefig(out_path)
    print(f"绘图已保存至 {out_path}")

    # 如果当前环境支持图形界面，显示窗口
    try:
        plt.show()
    except Exception:
        pass

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, 'imu_data.csv')
    out_path = os.path.join(script_dir, 'imu_plot.png')

    data = read_csv(csv_path)
    plot_data(data, out_path)

if __name__ == '__main__':
    main()
