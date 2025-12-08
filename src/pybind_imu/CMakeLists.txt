cmake_minimum_required(VERSION 3.14)
project(imu_py LANGUAGES CXX)

# 使用 C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 查找 pybind11（已通过 pip 安装）
execute_process(COMMAND ${PYTHON_EXECUTABLE} -c "import pybind11; print(pybind11.get_cmake_dir())" OUTPUT_VARIABLE PYBIND11_CMAKE_DIR OUTPUT_STRIP_TRAILING_WHITESPACE)
set(CMAKE_PREFIX_PATH "${PYBIND11_CMAKE_DIR}" ${CMAKE_PREFIX_PATH})

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/..
)

find_package(pybind11 REQUIRED)

pybind11_add_module(imu_py
    pybind_imu.cpp
    ../dm_imu/imu_driver.cpp
    ../dm_imu/bsp_crc.cpp)

target_link_libraries(imu_py PRIVATE pthread)
