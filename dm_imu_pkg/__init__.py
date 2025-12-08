import pathlib
import importlib.util
import sys

def _load_imu_module():
    """
    Load the compiled pybind11 module ``imu_py``.
    When the package is installed via ``pip install .`` the shared object
    will be placed next to this ``__init__.py``. During development it may
    still reside in the build directory under ``src/pybind_imu/build``.
    """
    # 1. Try to import if the .so is already in the package directory.
    try:
        from . import imu_py  # type: ignore  # pylint: disable=import-error
        return imu_py
    except Exception:
        pass

    # 2. Fallback: locate the build output relative to the repository root.
    possible_paths = [
        pathlib.Path(__file__).parent.parent
        / "src"
        / "pybind_imu"
        / "build"
        / "imu_py.cpython-310-aarch64-linux-gnu.so",
        # Generic pattern for other Python versions / architectures
        pathlib.Path(__file__).parent.parent
        / "src"
        / "pybind_imu"
        / "build"
        / "imu_py.*.so",
    ]

    for p in possible_paths:
        # glob pattern handling for the generic case
        if "*" in str(p):
            matches = list(p.parent.glob(p.name))
            if matches:
                p = matches[0]
            else:
                continue
        if p.is_file():
            spec = importlib.util.spec_from_file_location("imu_py", p)
            imu_py = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(imu_py)  # type: ignore
            return imu_py

    raise ImportError(
        "Unable to locate the compiled 'imu_py' module. "
        "Make sure the package is installed with the compiled extension "
        "or run the build step before importing."
    )

# Expose the DmImu class at package level for convenience
_imu_mod = _load_imu_module()
DmImu = _imu_mod.DmImu
