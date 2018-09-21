"""
Atmosphere version.
"""
from subprocess import Popen, PIPE
from dateutil import parser

VERSION = (0, 14, 3, 'dev', 0)


def git_info(git_directory=None):
    if not git_directory:
        return None
    try:
        proc = Popen(
            "git --git-dir {} log -1 --format=format:%H%ci".
            format(git_directory),
            shell=True,
            stdout=PIPE,
            stderr=PIPE
        )
        return proc.communicate()[0]
    except OSError:
        return None


def git_branch(git_directory=None):
    if not git_directory:
        return None
    try:
        proc = Popen(
            (
                "git --git-dir {} rev-parse --symbolic-full-name "
                "--abbrev-ref HEAD"
            ).format(git_directory),
            shell=True,
            stdout=PIPE,
            stderr=PIPE
        )
        return proc.communicate()[0].replace("\n", "")
    except OSError:
        return None


def git_version_lookup(
    git_directory=None, git_branch_name=None, git_head_info=None
):
    """
    Generate a summary from git on the version
    """
    branch = git_branch_name or git_branch(git_directory=git_directory)
    info = git_head_info or git_info(git_directory=git_directory)

    git_sha = None
    git_sha_abbrev = None
    commit_date = None
    if info:
        git_sha = info[0:39]
        git_sha_abbrev = "@" + info[0:6]
        commit_date = parser.parse(info[40:])

    return {
        'git_sha': git_sha,
        'git_sha_abbrev': git_sha_abbrev,
        'commit_date': commit_date,
        'git_branch': branch
    }
