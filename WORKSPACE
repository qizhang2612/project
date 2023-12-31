### Setting up python rules
load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

http_archive(
    name = "rules_python",
    sha256 = "a868059c8c6dd6ad45a205cca04084c652cfe1852e6df2d5aca036f6e5438380",
    strip_prefix = "rules_python-0.14.0",
    url = "https://github.com/bazelbuild/rules_python/archive/refs/tags/0.14.0.tar.gz",
)

load("@rules_python//python:pip.bzl", "pip_parse")

# Create a central repo that knows about the dependencies needed from
# requirements_lock.txt.
pip_parse(
    name = "my_deps",
    extra_pip_args = [
        "--index-url",
        "https://pypi.tuna.tsinghua.edu.cn/simple",
    ],
    # Run `bazel run requirements.update` to generate requirements_lock.txt
    requirements_lock = "//third_party/py:requirements_lock.txt",
)

# Load the starlark macro which will define your dependencies.
load("@my_deps//:requirements.bzl", "install_deps")

# Call it to define repos for your requirements.
install_deps()

# Hedron's Compile Commands Extractor for Bazel
# https://github.com/hedronvision/bazel-compile-commands-extractor
# Generate compile_commands.json with command
#   bazel run @hedron_compile_commands//:refresh_all
http_archive(
    name = "hedron_compile_commands",
    # When you first run this tool, it'll recommend a sha256 hash to put here with a message like: "DEBUG: Rule 'hedron_compile_commands' indicated that a canonical reproducible form can be obtained by modifying arguments sha256 = ..."
    sha256 = "78776448d9684dc6d6f50f37c94014f1d1b054c392050214f61a3ddc5ece64e2",
    strip_prefix = "bazel-compile-commands-extractor-05610f52a2ea3cda6ac27133b96f71c36358adf9",

    # Replace the commit hash in both places (below) with the latest, rather than using the stale one here.
    # Even better, set up Renovate and let it do the work for you (see "Suggestion: Updates" in the README).
    url = "https://github.com/hedronvision/bazel-compile-commands-extractor/archive/05610f52a2ea3cda6ac27133b96f71c36358adf9.tar.gz",
)

load("@hedron_compile_commands//:workspace_setup.bzl", "hedron_compile_commands_setup")

hedron_compile_commands_setup()
