package(default_visibility = ["//visibility:public"])
load("@my_deps//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "stat",
    srcs = ["stat.py"],
    deps = [
        requirement("numpy"),
    ],
)
