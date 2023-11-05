package(default_visibility = ["//visibility:public"])

py_library(
    name = "packet_handler",
    srcs = ["packet_handler.py"],
    deps = [
        "//main/controller/manager:table_manager",
        "//main/dir_server/view:controller_view",
    ],
)

py_library(
    name = "topology_info",
    srcs = ["topology_info.py"],
    data = ["//main/controller/conf:static_topo.json"],
    deps = [
        "//main/controller/lib/utils:util",
    ],
)
