package(default_visibility = ["//visibility:public"])

py_binary(
    name = "run_controller",
    srcs = ["run_controller.py"],
    data = ["//main/controller/manager:controller.py"],
    deps = [
        "//main/controller/lib/net:packet_handler",
        "//main/controller/lib/net:topology_info",
        "//main/controller/lib/te:disjoint_set",
        "//main/controller/lib/te:span_tree",
        "//main/controller/manager:traffic_manager",
        "//main/dir_server/view:controller_view",
        "//main/pub_sub/server/manager:pub_sub_manager",
    ],
)
