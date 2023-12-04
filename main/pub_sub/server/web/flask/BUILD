package(default_visibility = ["//visibility:public"])

py_binary(
    name = "ps_database",
    srcs = ["ps_database.py"],
    data = [
        "//main/pub_sub/server/web/conf:front_end.yaml",
    ],
    deps = [
        "//main/dir_server/view:controller_view",
        "//main/dir_server/view:server_view",
    ],
)
