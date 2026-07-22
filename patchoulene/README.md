# patchoulene

Here lies some openRuyi patch tracking scripts.

## `ruyi-change-id.py`

A Git `prepare-commit-msg` hook for inserting Change-Id trailers on otherwise unidentified commit messages.
This hook checks the commit message on `git commit --amend [--signoff]` or `git rebase` "reword".
If it has no recognized identifier, a Change-Id trailer is added.

Usage:

```console
$ ln -s /path/to/patchoulene/ruyi-change-id.py .git/hooks/prepare-commit-msg
```
