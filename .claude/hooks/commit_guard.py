#!/usr/bin/env python3
"""Bypass-flag scan for the commit guard (block_commit_if_red.sh).

stdin: the PreToolUse hook JSON payload. stdout: one verdict line —
    allow             not a git commit; nothing to do
    commit            a git commit: the wrapper arms .githooks and allows
    deny <reason>     block (the wrapper exits 2)

The scan shlex-tokenizes the command with heredoc bodies stripped first, and
never scans `-m`/`--message`/`-F` argument tokens as flags — commit-message
prose discussing bypass flags must never trip it. It is an anti-footgun
guard, not a sandbox: quoting tricks can hide a flag from the tokenizer, but
any commit that executes is still gated by `.githooks/pre-commit` at commit
time, and the wrapper re-arms `core.hooksPath` on every commit attempt.
"""
import json
import re
import shlex
import sys

CONNECTORS = {"&&", "||", ";", "|", "&"}
MESSAGE_FLAGS = {"-m", "--message", "-F", "--file"}
# --no-verify plus git parse-options unique-prefix abbreviations (the net
# also catches --no-verbose; fail-closed is preferred over that rare loss).
NO_VERIFY = re.compile(r"--no-ve\w*$")
SHORT_CLUSTER = re.compile(r"-[a-zA-Z]+$")


def strip_heredocs(text):
    """Drop heredoc body lines (and the terminator) so message prose is
    never tokenized; the line carrying the `<<MARKER` itself is kept."""
    out, term = [], None
    for line in text.split("\n"):
        if term is not None:
            if line.strip() == term:
                term = None
            continue
        m = re.search(r"<<-?\s*([\"']?)(\w+)\1", line)
        out.append(line)
        if m:
            term = m.group(2)
    return "\n".join(out)


def is_git(tok):
    return tok == "git" or tok.endswith("/git")


# core.hooksPath read-only inspection flags — `git config --get core.hooksPath`
# and friends are reads, not manipulation, and must not be denied.
CONFIG_READ_FLAGS = {"--get", "--get-all", "--get-regexp", "--list", "-l"}


def sets_hookspath(seg, i):
    """True when token ``seg[i]`` (which contains ``core.hooksPath``) is
    actually *setting* the value rather than reading it. The set forms:
    ``-c core.hooksPath=VALUE`` / env ``GIT_CONFIG_*=…core.hooksPath`` (the
    ``key=value`` shape always carries ``=``), and ``git config [opts]
    core.hooksPath VALUE`` (a value token follows the key, and no read-mode
    flag is present). A bare ``git config core.hooksPath`` / ``--get
    core.hooksPath`` is a read."""
    tok = seg[i]
    if "core.hooksPath=" in tok:
        return True  # -c key=val / GIT_CONFIG env injection
    if "config" not in seg[:i]:
        return False  # not a `git config` invocation — can't be a config set
    if any(f in seg for f in CONFIG_READ_FLAGS):
        return False  # explicit read mode
    rest = seg[i + 1:]
    return any(not t.startswith("-") for t in rest)  # a value follows the key


def verdict(cmd):
    if not ("git" in cmd and ("commit" in cmd or "core.hooksPath" in cmd)):
        return "allow"
    stripped = strip_heredocs(cmd)
    try:
        tokens = shlex.split(stripped, posix=True)
    except ValueError:
        return ("deny the command could not be tokenized to scan for bypass "
                "flags (unbalanced quoting after heredoc-stripping) — "
                "rewrite the commit more plainly")

    segments, cur = [], []
    for t in tokens:
        if t in CONNECTORS:
            segments.append(cur)
            cur = []
        else:
            cur.append(t)
    segments.append(cur)

    found_commit = False
    for seg in segments:
        gi = next((i for i, t in enumerate(seg) if is_git(t)), None)
        if gi is None:
            continue
        # core.hooksPath *manipulation* in any git segment (config set, -c
        # override, GIT_CONFIG_* env) is reserved to the guard itself; a bare
        # read (`git config --get core.hooksPath`) is left alone.
        for i, t in enumerate(seg):
            if ("core.hooksPath" in t and (i == 0 or seg[i - 1] not in MESSAGE_FLAGS)
                    and sets_hookspath(seg, i)):
                return "deny core.hooksPath manipulation is reserved to the commit guard"
        rest = seg[gi + 1:]
        if "commit" not in rest:
            continue
        found_commit = True
        args = rest[rest.index("commit") + 1:]
        skip_next = False
        for t in args:
            if skip_next:
                skip_next = False
                continue
            if t in MESSAGE_FLAGS:
                skip_next = True
                continue
            if NO_VERIFY.match(t):
                return "deny --no-verify (and its abbreviations) cannot bypass the gate"
            if SHORT_CLUSTER.match(t) and "n" in t:
                return "deny a short-flag cluster carrying -n (--no-verify) cannot bypass the gate"
    if found_commit:
        return "commit"
    # `git` + `commit` substrings present but no parseable git-commit segment
    # (e.g. quoted `sh -c 'git commit …'`): fail closed on a bypass substring,
    # otherwise treat as a commit so the wrapper arms the githook. Match the
    # core.hooksPath *set* form (`-c core.hooksPath=` / GIT_CONFIG env) only —
    # a bare `core.hooksPath` substring here is a read (`grep`/`--get`), not a
    # bypass, and must not be denied.
    if "--no-verify" in stripped or "core.hooksPath=" in stripped:
        return ("deny a bypass flag appears in an unparseable position — "
                "rewrite the commit as a plain `git commit` invocation")
    return "commit"


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        d = {}
    cmd = (d.get("tool_input") or {}).get("command", "") or ""
    print(verdict(cmd))


if __name__ == "__main__":
    main()
