#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "imu_driver.h"

namespace py = pybind11;
using namespace dmbot_serial;

/* Convert IMU_Data to a Python dict */
py::dict imu_data_to_dict(const IMU_Data &data) {
    py::dict d;
    d["accx"]   = data.accx;
    d["accy"]   = data.accy;
    d["accz"]   = data.accz;
    d["gyrox"]  = data.gyrox;
    d["gyroy"]  = data.gyroy;
    d["gyroz"]  = data.gyroz;
    d["roll"]   = data.roll;
    d["pitch"]  = data.pitch;
    d["yaw"]    = data.yaw;
    return d;
}

PYBIND11_MODULE(imu_py, m) {
    m.doc() = "Python bindings for DM‑IMU driver";

    py::class_<DmImu>(m, "DmImu")
        .def(py::init<const std::string&, int>(),
             py::arg("port") = "/dev/ttyACM1",
             py::arg("baud") = 921600)
        .def("start", &DmImu::start)
        .def("stop",  &DmImu::stop)
        .def("getData",
             [](const DmImu &self) {
                 return imu_data_to_dict(self.getData());
             });
}
