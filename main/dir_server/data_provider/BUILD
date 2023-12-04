package(default_visibility = ["//visibility:public"])

py_library(
    name = "data_provider",
    srcs = ["data_provider.py"],
    data = [
        "//main/dir_server/conf:host_config.yaml",
        "//main/dir_server/conf:server_config.yaml",
    ],
    deps = [
        "//main/dir_server/data_service:mysql_manager",
        "//main/dir_server/data_service:redis_manager",
    ],
)
