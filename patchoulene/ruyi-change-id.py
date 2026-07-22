#!/usr/bin/env python

import datetime
import os
import re
import shlex
import subprocess
import sys

RE_CHERRY = re.compile(
    r"^\(cherry picked from commit (?P<commit>[0-9a-f]+)\)$", re.MULTILINE
)
RE_CHERRY_TREE = re.compile(
    r"^\(cherry picked from commit (?P<commit>[0-9a-f]+)[ \t]*\n[ \t]+(?P<tree>\S+)[ \t]+(?P<branch>\S+)\)$",
    re.MULTILINE,
)
RE_LINK = re.compile(
    r"^Link:[ \t]+(?:https://lore\.kernel\.org/r/|https://patch\.msgid\.link/)(?P<msgid>[^\s/]+)/?(?:[ \t]*$|[ \t]+#)",
    re.MULTILINE,
)
RE_CHANGE_ID = re.compile(r"^(\w+-)*Change-Id:[ \t]+(\w+:\S+)$", re.MULTILINE)


def message_subject(message: str) -> str:
    """
    The first line of a message, or the empty string if the message is empty.
    """
    return (message.split("\n", 1) + [""])[0]


def clean_subject(subject: str) -> str:
    """
    Remove prefixes from commit message subject.
    Vendor prefixes (except RUYI) are *not* removed.
    """
    return re.sub(r"^(?:(?:FROMLIST|FROMGIT|UPSTREAM|BACKPORT|RUYI): )*", "", subject)


def sanitize_subject(subject: str) -> str:
    """
    Convert subject to a filename safe format.
    This is a reimplementation of Git's log format %f.
    """
    # https://github.com/git/git/blob/v2.55.0/pretty.c#L947
    # Safe chars: ASCII alphanumeric, '.', '_'

    # Replace runs of other chars with one dash
    subject = re.sub(r"[^a-zA-Z0-9._]+", "-", subject)
    # Replace runs of multiple dots with one
    subject = re.sub(r"\.+", ".", subject)
    # Remove dashes at start or end
    return re.sub("^-+|-+$", "", subject)


def gen_change_id(message):
    base = sanitize_subject(clean_subject(message_subject(message)))
    datepart = datetime.datetime.now().strftime("%Y%m%d")
    return f"{base}-{datepart}"


def cur_branch() -> str | None:
    """
    Get the current branch or current rebasing in the Git repository in the current directory.
    Returns the branch name, or None if none could be determined.
    """
    cur_branch = subprocess.check_output(
        shlex.split("git rev-parse --abbrev-ref HEAD"), encoding="utf-8"
    ).rstrip("\n")
    if cur_branch != "HEAD" and cur_branch != "":
        return cur_branch

    rebase_head_file = subprocess.check_output(
        shlex.split("git rev-parse --git-path rebase-merge/head-name"), encoding="utf-8"
    ).rstrip("\n")
    try:
        with open(rebase_head_file, "r") as f:
            rebase_head = f.read().rstrip("\n")
    except FileNotFoundError:
        return None

    if not rebase_head.startswith("refs/"):
        return None

    rebase_head = subprocess.check_output(
        shlex.split("git rev-parse --abbrev-ref") + [rebase_head], encoding="utf-8"
    ).rstrip("\n")

    return rebase_head


def main():
    msg_file, msg_source = sys.argv[1], sys.argv[2]

    if msg_source != "commit":
        return

    if os.getenv("RUYI_FORCE_CHANGE_ID", "") == "":
        b = cur_branch()
        if b is None or not b.startswith("ruyi/"):
            return

    with open(msg_file, "r") as f:
        commit_msg = f.read()

    if message_subject(commit_msg).strip() == "":
        return

    # Skip if we have a recognized identifier
    if any(
        r.search(commit_msg) for r in [RE_CHERRY, RE_CHERRY_TREE, RE_LINK, RE_CHANGE_ID]
    ):
        return

    # Okay, we need to insert an identifier.

    # Find insertion point before last Signed-off-by and bracketed note.
    #
    # (insert here)
    # [ Author: Something, something
    #   something more. ]
    # Signed-off-by: Author <author@example.com>
    matches = list(
        re.finditer(r"^(?:\[.*\n(?:\s.*\n)*)?Signed-off-by:", commit_msg, re.MULTILINE)
    )
    if not matches:
        return
    match = matches[-1]

    change_id = gen_change_id(commit_msg)

    # This is so the user still knows what happens after exiting the editor
    print(f"(ruyi) Generated Change-Id: {change_id}", file=sys.stderr)

    insert = f"""# !!! Automatically generated Change-Id
Change-Id: ruyi:{change_id}
# !!! ^^^^^^
"""
    new_msg = commit_msg[: match.span()[0]] + insert + commit_msg[match.span()[0] :]

    with open(msg_file, "w") as f:
        f.write(new_msg)


if __name__ == "__main__":
    main()
