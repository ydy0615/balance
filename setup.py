import pathlib
import sys
import os
from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext

class CMakeExtension(Extension):
    """
    A custom setuptools Extension that knows how to invoke CMake.
    """
    def __init__(self, name, sourcedir=""):
        super().__init__(name, sources=[])
        self.sourcedir = pathlib.Path(sourcedir).resolve()

class CMakeBuild(build_ext):
    """
    Build the CMake project when ``python setup.py build_ext`` is invoked.
    """
    def run(self):
        # Verify that CMake is installed.
        try:
            self.spawn(["cmake", "--version"])
        except OSError as e:
            raise RuntimeError("CMake must be installed to build the extensions") from e

        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        extdir = pathlib.Path(self.get_ext_fullpath(ext.name)).parent.resolve()
        cfg = "Release"

        # Ensure the build directory exists.
        build_temp = pathlib.Path(self.build_temp) / ext.name
        build_temp.mkdir(parents=True, exist_ok=True)

        cmake_args = [
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={extdir}",
            f"-DPYTHON_EXECUTABLE={sys.executable}",
            f"-DCMAKE_BUILD_TYPE={cfg}",
        ]

        # 1) configure
        os.chdir(str(build_temp))
        self.spawn(["cmake", str(ext.sourcedir)] + cmake_args)
        # 2) build
        self.spawn(
            ["cmake", "--build", ".", "--config", cfg, "--", f"-j{os.cpu_count() or 1}"],
        )

# Path to the pybind11 C++ source directory.
pybind_src = pathlib.Path(__file__).parent / "dm_imu"

setup(
    name="dm_imu",
    version="0.1.0",
    author="allenyuan",
    description="DM IMU driver with pybind11",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    packages=["dm_imu"],
    ext_modules=[CMakeExtension("imu_py", sourcedir=str(pybind_src))],
    cmdclass={"build_ext": CMakeBuild},
    zip_safe=False,
    python_requires=">=3.8",

    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
