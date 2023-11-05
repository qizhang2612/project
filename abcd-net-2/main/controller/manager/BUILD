package(default_visibility = ["//visibility:public"])

exports_files(["controller.py"])

py_library(
    name = "table_manager",
    srcs = ["table_manager.py"],
    deps = [
        "//main/controller/lib/te:sdn_node",
    ],
)

py_library(
    name = "traffic_manager",
    srcs = ["traffic_manager.py"],
    deps = [
        "//main/controller/lib/te:multicast_tree",
    ],
)

py_library(
    name = "controller",
    srcs = ["controller.py"],
)
