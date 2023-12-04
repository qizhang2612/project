package(default_visibility = ["//visibility:public"])

py_library(
    name = "host_view",
    srcs = ["host_view.py"],
    data = ["//main/dir_server/conf:host_config.yaml"],
    deps = ["//main/dir_server/data_provider"],
)

py_library(
    name = "server_view",
    srcs = ["server_view.py"],
    data = ["//main/dir_server/conf:server_config.yaml"],
    deps = ["//main/dir_server/data_provider"],
)

py_library(
    name = "controller_view",
    srcs = ["controller_view.py"],
    data = ["//main/dir_server/conf:server_config.yaml"],
    deps = ["//main/dir_server/data_provider"],
)
