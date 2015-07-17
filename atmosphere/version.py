"""
Atmosphere version.
"""
from dateutil import parser
from os.path import abspath, dirname
from subprocess import Popen, PIPE


VERSION = (0, 14, 3, 'dev', 0)


def git_info():
    loc = abspath(dirname(__file__))
    try:
        p = Popen(
            "cd \"%s\" && git log -1 --format=format:%%H%%ci" % loc,
            shell=True,
            stdout=PIPE,
            stderr=PIPE
        )
        return p.communicate()[0]
    except OSError:
        return None


def git_branch():
    loc = abspath(dirname(__file__))
    try:
        p = Popen(
            "cd \"%s\" && git "
            "rev-parse --symbolic-full-name --abbrev-ref HEAD" % loc,
            shell=True,
            stdout=PIPE,
            stderr=PIPE)
        return p.communicate()[0].replace("\n", "")
    except OSError:
        return None


def get_version(form='short'):
    """
    Returns the version string.

    Takes single argument ``form``, which should be one of the following
    strings:

    * ``short`` Returns major + minor branch version string with the format of
    B.b.t.
    * ``normal`` Returns human readable version string with the format of
    B.b.t _type type_num.
    * ``verbose`` Returns a verbose version string with the format of
    B.b.t _type type_num@git_sha_abbrev
    * ``all`` Returns a dict of all versions.
    """
    versions = {}
    branch = "%s.%s" % (VERSION[0], VERSION[1])
    tertiary = VERSION[2]
    type_ = VERSION[3]
    type_num = VERSION[4]

    versions["branch"] = branch
    v = versions["branch"]
    if tertiary:
        versions["tertiary"] = "." + str(tertiary)
        v += versions["tertiary"]
    versions['short'] = v
    if form is "short":
        return v
    v += " " + type_ + " " + str(type_num)
    versions["normal"] = v
    if form is "normal":
        return v
    info = git_info()
    versions["git_sha"] = info[0:39]
    versions["git_sha_abbrev"] = "@" + info[0:6]
    versions["git_branch"] = git_branch()
    versions["commit_date"] = parser.parse(info[40:])
    v += " " + versions["git_sha_abbrev"]
    versions["verbose"] = v
    if form is "verbose":
        return v
    if form is "all":
        return versions
