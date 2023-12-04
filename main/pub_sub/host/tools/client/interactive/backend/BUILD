package(default_visibility = ["//visibility:public"])

py_binary(
    name = "back",
    srcs = ["back.py"],
    deps = [
        "//lib/py/json",
        "//lib/py/net:util",
        "//main/dir_server/view:host_view",
    ],
    data = ["//main/pub_sub/host/conf/info:ip.json"]
)

py_binary(
    name = "controller_listener",
    srcs = ["controller_listener.py"],
    data = [
        "//main/pub_sub/host/conf/info:host_info.json",
        "//main/pub_sub/host/conf/info:ip.json",
    ],
    deps = [
        "//lib/py/json",
        "//lib/py/net:util",
    ],
)
