package(default_visibility = ["//visibility:public"])

py_binary(
    name = "run_ps_web",
    srcs = ["run_ps_web.py"],
    data = [
        "//main/pub_sub/server/conf:server_info.json",
    ],
    deps = [
        "//main/pub_sub/server/manager:pub_sub_manager",
    ],
)
