package(default_visibility = ["//visibility:public"])

py_binary(
    name = "recv",
    srcs = ["recv.py"],
    data = [
        "//main/pub_sub/host/conf/info:host_info.json",
        "//main/pub_sub/host/conf/info:ip.json",
    ],
    deps = [
        "//lib/py/json",
        "//lib/py/net:util",
    ],
)

py_binary(
    name = "send",
    srcs = ["send.py"],
    data = [
        "//main/pub_sub/host/conf/info:host_info.json",
        "//main/pub_sub/host/conf/info:ip.json",
    ],
    deps = [
        "//lib/py/json",
        "//lib/py/net:util",
    ],
)

py_binary(
    name = "found",
    srcs = ["found.py"],
    data = [
        "//main/pub_sub/host/conf/info:host_info.json",
        "//main/pub_sub/host/conf/info:ip.json",
    ],
    deps = [
        "//lib/py/json",
        "//lib/py/net:util",
    ],
)
