package(default_visibility = ["//visibility:public"])
load("@my_deps//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary")

py_binary(
    name = "plot-iperf3-goodput",
    srcs = ["plot-iperf3-goodput.py"],
    deps = [
        "//lib/py/plot:plot",
        "//lib/py/net:iperf3",
        requirement("numpy"),
        requirement("matplotlib"),
        requirement("pandas"),
    ]
)

