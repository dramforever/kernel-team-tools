import re

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
RE_CHANGE_ID = re.compile(r"^(\w+-)*Change-Id:[ \t]+(?P<id>\w+:\S+)$", re.MULTILINE)

RE_LINK_UPSTREAM = re.compile(
    r"^Link:[ \t]+(?:https://patch\.msgid\.link/)(?P<msgid>[^\s/]+)/?(?:[ \t]*$|[ \t]+#)",
    re.MULTILINE,
)
RE_STABLE_BACKPORT_1 = re.compile(
    r"^\[ [Uu]pstream commit (?P<commit>[0-9a-f]+) \]$", re.MULTILINE
)
RE_STABLE_BACKPORT_2 = re.compile(
    r"^[Cc]ommit (?P<commit>[0-9a-f]+) upstream\W*$", re.MULTILINE
)


def guess_id(message: str) -> list[str]:
    candidates = []

    for cherry in RE_CHERRY.finditer(message):
        candidates.append((cherry.span(1), f"commit:{cherry['commit']}"))

    # Might not be stable, not used for now

    # for cherry_tree in RE_CHERRY_TREE.finditer(message):
    #     candidates.append(
    #         (
    #             cherry_tree.span(1),
    #             f"commit:{cherry_tree['commit']},{cherry_tree['tree']}#{cherry_tree['branch']}",
    #         )
    #     )

    for link in RE_LINK.finditer(message):
        candidates.append((link.span(1), f"mail:{link['msgid']}"))

    for change_id in RE_CHANGE_ID.finditer(message):
        candidates.append((change_id.span(1), f"changeid:{change_id['id']}"))

    # Appearing later in the message is better
    return [c[1] for c in sorted(candidates, key=lambda c: c[0], reverse=True)]


def guess_upstream_id(message: str) -> list[str]:
    return (
        [
            f"commit:{commit['commit']}"
            for commit in RE_STABLE_BACKPORT_1.finditer(message)
        ]
        + [
            f"commit:{commit['commit']}"
            for commit in RE_STABLE_BACKPORT_2.finditer(message)
        ]
        + [f"commit:{commit['commit']}" for commit in RE_CHERRY.finditer(message)]
        + [f"mail:{link['msgid']}" for link in RE_LINK_UPSTREAM.finditer(message)][::-1]
    )


def message_subject(message: str) -> str:
    return (message.split("\n", 1) + [""])[0]


def clean_subject(message: str) -> str:
    subject = message_subject(message)
    return re.sub(r"^(?:(?:FROMLIST|FROMGIT|UPSTREAM|BACKPORT|RUYI): )*", "", subject)


def check_message(message: str) -> list[str]:
    problems = []

    # The five(?) sins of Git commit messages
    # - Diff starts: /^diff -/, /^Index: /, /^---([ \t]*$| )/
    # - Author-overriding From: lines ("From" is case-insensitive)
    # - "mbox" "From" lines (See is_from_line() from Git builtin/mailsplit.c)
    matches = re.finditer(
        r"^(?:diff -|Index: |---(?:[ \t]*$| )|(?i:From):|(?=.{20})From .*\d.\d\d:\d\d[^:](?:0*9[1-9]|0*[1-9][0-9]{2,})[^:]*$).*$",
        message,
        re.MULTILINE,
    )
    for m in matches:
        problems.append(f"Message line {m[0]!r} confuses git am")

    if not guess_id(message):
        problems.append("Message has no identifier")

    return problems


def sanitize_subject(subject: str) -> str:
    # https://github.com/git/git/blob/v2.55.0/pretty.c#L947
    # Safe chars: ASCII alphanumeric, '.', '_'

    # Replace runs of other chars with one dash
    subject = re.sub(r"[^a-zA-Z0-9._]+", "-", subject)
    # Replace runs of multiple dots with one
    subject = re.sub(r"\.+", ".", subject)
    # Remove dashes at start or end
    return re.sub("^-+|-+$", "", subject)
