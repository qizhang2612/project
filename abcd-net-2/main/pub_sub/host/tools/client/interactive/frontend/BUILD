package(default_visibility = ["//visibility:public"])

py_binary(
    name = "interactive",
    srcs = ["interactive.py"],
    data = [
        "//main/pub_sub/host/conf/info:host_info.json",
        "//main/pub_sub/host/conf/info:ip.json",
    ],
    deps = [
        "//lib/py/json",
        "//lib/py/net:util",
    ],
)
