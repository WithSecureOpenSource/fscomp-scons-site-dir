# Copyright 2020 Emanuele Giaquinta

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

import SCons
from SCons.Tool.cc import CSuffixes

CXXSuffixes = [".cpp", ".cc", ".cxx", ".c++", ".C++", ".mm"]
if SCons.Util.case_sensitive_suffixes(".c", ".C"):
    CXXSuffixes.append(".C")


def add_compilation_db_emitter(builder, suffix, command):
    user_action = SCons.Action.Action(command)

    def emit_compilation_db_entry(target, source, env):
        command = user_action.strfunction(
            target=target,
            source=source,
            env=env,
        )

        if source[0].srcnode().exists():
            source_node = source[0].srcnode()
        else:
            source_node = source[0]

        entry = {
            "directory": target[0].dir.abspath,
            "command": command,
            "file": source_node.abspath,
        }

        env["_COMPILATION_DB"].append(entry)

        return target, source

    emitter = SCons.Builder.ListEmitter(
        [builder.emitter[suffix], emit_compilation_db_entry]
    )
    builder.add_emitter(suffix, emitter)


def get_compilation_db_node(node, env, path):
    return [SCons.Node.Python.Value(env["_COMPILATION_DB"])]


def generate(env, **kwargs):
    static_obj, shared_obj = SCons.Tool.createObjBuilders(env)

    for suffix in CSuffixes:
        add_compilation_db_emitter(static_obj, suffix, "$CCCOM")
        add_compilation_db_emitter(shared_obj, suffix, "$SHCCCOM")
    for suffix in CXXSuffixes:
        add_compilation_db_emitter(static_obj, suffix, "$CXXCOM")
        add_compilation_db_emitter(shared_obj, suffix, "$SHCXXCOM")

    env["_COMPILATION_DB"] = []

    def get_compilation_db(env):
        return env["_COMPILATION_DB"]

    env.AddMethod(get_compilation_db, "GetCompilationDB")

    def set_compilation_db(env, db):
        env["_COMPILATION_DB"] = db

    env.AddMethod(set_compilation_db, "SetCompilationDB")

    def write_compilation_db(target, source, env):
        with open(target[0].path, "w", encoding="utf-8") as f:
            json.dump(
                env["_COMPILATION_DB"],
                f,
                indent=2,
                sort_keys=True,
            )

    env["BUILDERS"]["_CompilationDB"] = SCons.Builder.Builder(
        action=SCons.Action.Action(write_compilation_db),
        target_scanner=SCons.Scanner.Scanner(
            function=get_compilation_db_node, node_class=None
        ),
    )

    def compilation_db(env, target):
        return env._CompilationDB(target, None)

    env.AddMethod(compilation_db, "CompilationDB")


def exists(env):
    return True
