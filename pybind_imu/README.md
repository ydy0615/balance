# Pybind11 Wrapper for DM‑IMU Driver

## Overview
This project provides a **Python module** that wraps the `DmImu` class from the `dm_imu` driver library using **pybind11**.  
After building, you obtain a shared object (`imu_py*.so`) that can be imported in Python to control the IMU, start data acquisition, and retrieve sensor readings as a Python `dict`.

## Prerequisites
| Requirement | Version / Notes |
|------------|-----------------|
| **C++ compiler** | GCC 11 (or newer) |
| **CMake** | ≥ 3.14 |
| **Python** | 3.8 – 3.12 (the build uses the interpreter found by CMake) |
| **pybind11** | Installed via `pip install pybind11` (the package provides the CMake config) |
| **Serial port access** | The user must have read/write permission for the device (e.g., `/dev/ttyACM1`). See *Serial Port Permissions* below. |

## Build Steps
```bash
# 1. Install pybind11 (if not already installed)
pip install --user pybind11

# 2. Clone / copy this repository (already present in /home/allenyuan/balance)

# 3. Build the Python extension
cd pybind_imu
rm -rf build
mkdir build && cd build
cmake ..          # CMake will locate pybind11 automatically
make -j$(nproc)   # Builds imu_py.cpython-<ver>-<arch>.so
```

The compiled shared library will be placed in `pybind_imu/build/`.

## Installing the Module (optional)
You can copy the generated `.so` file to a location that is on `PYTHONPATH`, for example:

```bash
cp build/imu_py.cpython-310-aarch64-linux-gnu.so ~/.local/lib/python3.10/site-packages/

cp build/imu_py.cpython-310-aarch64-linux-gnu.so /home/allenyuan/miniconda3/lib/python3.13/site-packages
```

Or simply import it directly from the `build` directory (see the example below).

## Serial Port Permissions
If you encounter the error:

```
Failed to open IMU serial port: /dev/ttyACM1
```

you have two options:

1. **Run the Python script with sudo** (quick test):
   ```bash
   sudo python3 example.py
   ```

2. **Add your user to the dialout group** (recommended):
   ```bash
   sudo usermod -aG dialout $USER
   # Log out and log back in for the group change to take effect
   ```

## Usage from Python
```python
import pathlib
import importlib.util

# Load the compiled module (adjust the path if you installed it elsewhere)
lib_path = pathlib.Path('pybind_imu/build/imu_py.cpython-310-aarch64-linux-gnu.so')
spec = importlib.util.spec_from_file_location('imu_py', lib_path)
imu_py = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imu_py)

# Create an IMU instance (default port and baud rate are shown)
imu = imu_py.DmImu('/dev/ttyACM1', 921600)

# Start data acquisition (spawns a background thread)
imu.start()

# Retrieve a single measurement
data = imu.getData()
print('IMU data:', data)

# When finished, stop the thread and close the serial port
imu.stop()
```

## Example Program
A ready‑to‑run example is provided as `example.py` in this directory. It demonstrates:

* Loading the module
* Starting the driver
* Reading data in a loop
* Clean shutdown on `KeyboardInterrupt`

Run it with:

```bash
python3 example.py
```

## Troubleshooting
| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| CMake cannot find `pybind11` | `pybind11` not installed or not on `CMAKE_PREFIX_PATH` | `pip install --user pybind11` and ensure `CMAKE_PREFIX_PATH` points to `~/.local/lib/python3.10/site-packages/pybind11/share/cmake` (the CMakeLists already sets this). |
| Compilation error: `dm_imu/imu_driver.h: No such file or directory` | Include path wrong | The CMake file uses `include_directories(${CMAKE_CURRENT_SOURCE_DIR}/..)` which points to the project root where `dm_imu` resides. |
| Runtime: “Failed to open IMU serial port” | No permission on the device | Use `sudo` or add user to `dialout` group (see above). |
| Python import error “module not found” | Wrong path to the `.so` file | Adjust `lib_path` in the Python code to point to the actual location of the compiled shared object. |

---

**Enjoy!** Feel free to adapt the wrapper for additional driver functionality or integrate it into larger Python applications. If you have any questions, open an issue in the repository or contact the maintainer.
