package(default_visibility = ["//visibility:public"])

load("@my_deps//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "iperf3",
    srcs = ["iperf3.py"],
    deps = [
        requirement("numpy"),
        requirement("matplotlib"),
        requirement("pandas"),
    ],
)

py_library(
    name = "util",
    srcs = ["util.py"],
    deps = [
        "//lib/py/json",
    ],
)

py_library(
    name = "non_block_socket",
    srcs = ["non_block_socket.py"],
)
