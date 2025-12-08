#!/usr/bin/env python3
"""
example.py – Demonstrates how to use the pybind11‑wrapped DM‑IMU driver.

Prerequisites
-------------
* The compiled shared library `imu_py*.so` must exist (see README.md for build steps).
* The current user must have read/write access to the IMU serial device
  (e.g. /dev/ttyACM1).  Use `sudo` or add the user to the `dialout` group
  if necessary.

Usage
-----
$ python3 example.py
"""

import pathlib
import importlib.util
import sys
import signal
import time

# ----------------------------------------------------------------------
# Load the compiled extension module.
# Adjust the path if you installed the .so elsewhere.
# ----------------------------------------------------------------------
module_path = pathlib.Path(__file__).parent / "build" / "imu_py.cpython-310-aarch64-linux-gnu.so"
if not module_path.is_file():
    sys.stderr.write(f"Error: compiled module not found at {module_path}\n")
    sys.exit(1)

spec = importlib.util.spec_from_file_location("imu_py", module_path)
imu_py = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imu_py)

# ----------------------------------------------------------------------
# Helper to cleanly stop the IMU thread on SIGINT / SIGTERM.
# ----------------------------------------------------------------------
def _signal_handler(sig, frame):
    print("\nReceived interrupt – stopping IMU...")
    imu.stop()
    sys.exit(0)

signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# ----------------------------------------------------------------------
# Create an IMU instance.
# You can change the serial port or baud rate if your hardware differs.
# ----------------------------------------------------------------------
imu = imu_py.DmImu("/dev/ttyACM0", 921600)

print("Starting IMU data acquisition...")
imu.start()

print("Press Ctrl‑C to stop.\n")
try:
    while True:
        data = imu.getData()
        # Pretty‑print the dictionary; you may replace this with logging, saving, etc.
        print(
            f"acc: ({data['accx']:.3f}, {data['accy']:.3f}, {data['accz']:.3f})  "
            f"gyro: ({data['gyrox']:.3f}, {data['gyroy']:.3f}, {data['gyroz']:.3f})  "
            f"euler: (roll={data['roll']:.2f}, pitch={data['pitch']:.2f}, yaw={data['yaw']:.2f})"
        )
        # Adjust the sleep interval as needed (here we poll at ~10 Hz).
        time.sleep(0.01)
except KeyboardInterrupt:
    # Fallback in case the signal handler missed the interrupt.
    _signal_handler(None, None)
