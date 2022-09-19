import os
import SCons.Script

def _init():
    global HOST_ARCH
    HOST_ARCH = _get_host_arch()
    global STAGE
    STAGE = SCons.Script.Dir(os.getenv("FSSTAGE", "#stage")).abspath

class FSEnvError(Exception):
    pass

def tools_generate(env, **kw):
    if "ARCH" not in env:
        raise FSEnvError("ARCH not specified in environment")
    env["STAGE"] = STAGE
    env["ARCHBUILDDIR"] = os.path.join(env["STAGE"], env["ARCH"], "build")
    env["HOST_ARCH"] = HOST_ARCH
    _add_config_parser(env)
    _add_lib_config_installer(env)
    _add_fstracecheck(env)

def _pkg_config_path(env):
    return os.path.join(env["PREFIX"], "lib", "pkgconfig")

def _add_config_parser(env):
    if "PKG_CONFIG_LIBS" in env:
        env["CONFIG_PARSER"] = " ".join([
            "pkg-config",
            "--static",
            "--cflags",
            "--libs"
        ] + env["PKG_CONFIG_LIBS"])
    else:
        env["CONFIG_PARSER"] = ""

def _add_lib_config_installer(env):
    def install_lib_config():
        name = env["NAME"]
        pkgconfig = env.Substfile(
            "lib/pkgconfig/" + name + ".pc",
            "#" + name + ".pc.in",
            SUBST_DICT={
                "@prefix@": env["PREFIX"],
                "@libs_private@": " ".join(
                    ["-L{}".format(path)
                     for path in env.get("TARGET_LIBPATH", [])] +
                    ["-l{}".format(lib)
                     for lib in env.get("TARGET_LIBS", [])] +
                    ["-Wl,-framework,{}".format(framework)
                     for framework in env.get("TARGET_FRAMEWORKS", [])]
                ),
            },
        )
        env.Alias(
            "install",
            env.Install(_pkg_config_path(env), pkgconfig),
        )
    env.FSEnvInstallLibConfig = install_lib_config
    env.FSEnvInstallCommonLibConfig = install_lib_config

def _set_pkg_config_path(env):
    value = _get_arch_envvar(env, "FSPKG_CONFIG_PATH")
    if not value:
        value = _pkg_config_path(env)
    env["ENV"]["PKG_CONFIG_PATH"] = value

def _append_macos_paths(env):
    if env["ARCH"] == "darwin":
        env.AppendENVPath("PATH", "/opt/local/bin")
        env.AppendENVPath("PATH", "/opt/homebrew/bin")

def consider_environment_variables(env):
    _override(env, "AR", "FSAR")
    _override(env, "CC", "FSCC")
    _override(env, "CXX", "FSCXX")
    _override(env, "RANLIB", "FSRANLIB")
    _override(env, "CCTOOLFLAGS", "FSCCTOOLFLAGS")
    _override(env, "CXXTOOLFLAGS", "FSCXXTOOLFLAGS")
    _override(env, "LINKTOOLFLAGS", "FSLINKTOOLFLAGS")
    _combine(env, "CCTOOLFLAGS", "CCFLAGS")
    _combine(env, "CXXTOOLFLAGS", "CXXFLAGS")
    _combine(env, "LINKTOOLFLAGS", "LINKFLAGS")
    _append(env, "CCFLAGS", "FSCCFLAGS")
    _append(env, "CXXFLAGS", "FSCXXFLAGS")
    _append(env, "LINKFLAGS", "FSLINKFLAGS")
    _set_pkg_config_path(env)
    _append_macos_paths(env)

def _override(env, param, envvar):
    value = _get_arch_envvar(env, envvar)
    if value:                   # empty counts as None
        env[param] = value

def _combine(env, param1, param2):
    if param1 in env:
        if param2 in env:
            env[param2] = "{} {}".format(env[param1], env[param2])
        else:
            env[param2] = env[param1]

def _append(env, param, envvar):
    value = _get_arch_envvar(env, envvar)
    if value:
        if param in env:
            env[param] = "{} {}".format(env[param], value)
        else:
            env[param] = value

def _get_arch_envvar(env, envvar):
    return os.getenv(
        "{}__{}".format(envvar, env["ARCH"]),
        os.getenv(envvar, None))

def _add_fstracecheck(env):
    env["FSTRACECHECK"] = os.path.join(env["PREFIX"], "bin", "fstracecheck")
    env["FSTRACECHECK2"] = os.path.join(env["PREFIX"], "bin", "fstracecheck2")

_arch_map = {
    ("Darwin", "arm64"): "darwin",
    ("Darwin", "x86_64"): "darwin",
    ("FreeBSD", "amd64"): "freebsd_amd64",
    ("Linux", "i686"): "linux32",
    ("Linux", "x86_64"): "linux64",
    ("Linux", "aarch64"): "linux_arm64",
    ("OpenBSD", "amd64"): "openbsd_amd64",
}

def _get_host_arch():
    uname_os, _, _, _, uname_cpu = os.uname()
    return _arch_map[uname_os, uname_cpu]

def target_architectures(filter=None):
    archs = os.getenv("FSARCHS", None)
    if archs:
        archs = set(archs.split(","))
    else:
        archs = {HOST_ARCH}
    if filter is not None:
        archs &= set(filter)
    return archs

if __name__ == "fsenv":
    _init()
