package(default_visibility = ["//visibility:public"])

py_library(
    name = "disjoint_set",
    srcs = ["disjoint_set.py"],
)

py_library(
    name = "multicast_tree",
    srcs = ["multicast_tree.py"],
    deps = [
        "//main/controller/lib/te:reserve_information",
        "//main/controller/lib/te:sdn_node",
        "//main/controller/manager:table_manager",
    ],
)

py_library(
    name = "sdn_node",
    srcs = ["sdn_node.py"],
)

py_library(
    name = "span_tree",
    srcs = ["span_tree.py"],
    deps = ["//main/controller/lib/net:topology_info"],
)

py_library(
    name = "reserve_information",
    srcs = ["reserve_information.py"],
)
