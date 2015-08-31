import argparse
import os
import sys

import git

project_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
# This is the default change file for the project
CHANGE_FILE = os.path.join(project_root, "CHANGES")


def create_changelog(args):
    g = git.Git(project_root)
    commit_range = "%s..%s" % (args.start, args.stop)
    commits = g.log("--date=short", "--format=%ad %h %s",  "--no-merges", commit_range).split("\n")

    if not len(commits):
        print "Please specify a valid commit range."
        sys.exit(1)

    if args.overwrite:
        mode = "w"
    else:
        mode = "a+w"

    with open(args.filename, mode) as fp:
        fp.write("Release version %s\n" % args.release_name)
        for commit in commits:
            fp.write("\t* %s\n" % commit)


def create_tag(args):
    repo = git.Repo(project_root)
    repo.create_tag(args.tag, ref=args.stop, force=True,
                    message="Release %s" % args.release_name)


def main():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("start", help="The first commit in the revision range.")
    parser.add_argument("stop", help="The last commit in the revision range.")
    parser.add_argument("release_name", help="The name of the release.")
    parser.add_argument("--overwrite", "-o", action="store_true", help="Overwrite the CHANGES file.")
    parser.add_argument("--filename", "-f", default=CHANGE_FILE, help="The name of the CHANGES file.")
    parser.add_argument("--tag", "-t", help="Tag the last commit with the tag.")
    args = parser.parse_args()
    create_changelog(args)
    if args.tag:
        create_tag(args)


if __name__ == "__main__":
    main()
