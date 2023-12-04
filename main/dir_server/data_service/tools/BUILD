package(default_visibility = ["//visibility:public"])

py_binary(
    name = "canal_listener",
    srcs = ["canal_listener.py"],
    data = [
        "//main/dir_server/conf:host_config.yaml",
        "//main/dir_server/conf:server_config.yaml",
    ],
    deps = ["//main/dir_server/data_service:redis_manager"],
)
