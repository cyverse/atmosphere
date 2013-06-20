"""
System calls that get used all the time..
"""
import glob
import os
import subprocess

from threepio import logger

def run_command(commandList, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                stdin=None, dry_run=False):
    """
    NOTE: Use this to run ANY system command, because its wrapped around a loggger
    Using Popen, run any command at the system level and record the output and error streams
    """
    out = None
    err = None
    cmd_str = ' '.join(commandList)
    if dry_run:
        #Bail before making the call
        logger.debug("Mock Command: %s" % cmd_str)
        return ('','')
    try:
        if stdin:
            proc = subprocess.Popen(commandList, stdout=stdout, stderr=stderr, stdin=subprocess.PIPE)
        else:
            proc = subprocess.Popen(commandList, stdout=stdout, stderr=stderr)
        out,err = proc.communicate(input=stdin)
    except Exception, e:
        logger.error(e)
    if stdin:
        logger.debug("%s STDIN: %s" % (cmd_str, stdin))
    logger.debug("%s STDOUT: %s" % (cmd_str, out))
    logger.debug("%s STDERR: %s" % (cmd_str, err))
    return (out,err)


def overwrite_file(filepath, dry_run=False):
    if not os.path.exists(filepath):
        logger.warn("Cannot remove lines from non-existent file: %s" %
                filepath)
        return
    cmd_list = ['/bin/cp', '-f', '/dev/null', '%s' % filepath]
    run_command(cmd_list, dry_run=dry_run)


def wildcard_remove(wildcard_path, dry_run=False):
    """
    Expand the wildcard to match all files, delete each one.
    """
    logger.debug(wildcard_path)
    glob_list = glob.glob(wildcard_path)
    if glob_list:
        for filename in glob_list:
            cmd_list = ['/bin/rm', '-rf', filename]
            run_command(cmd_list, dry_run=dry_run)

"""
SED tools - in-place editing of files on the system
BE VERY CAREFUL USING THESE -- YOU HAVE BEEN WARNED!
"""
def sed_delete_multi(from_here,to_here,filepath, dry_run=False):
    if not os.path.exists(filepath):
        raise Exception("Cannot remove lines from non-existent file: %s" %
                filepath)
    cmd_list = ["/bin/sed", "-i", "/%s/,/%s/d" % (from_here, to_here),
                filepath]
    run_command(cmd_list, dry_run=dry_run)

def sed_replace(find,replace,filepath, dry_run=False):
    if not os.path.exists(filepath):
        raise Exception("Cannot replace line from non-existent file: %s" %
                filepath)
    cmd_list = ["/bin/sed", "-i", "s/%s/%s/" % (find,replace), filepath]
    run_command(cmd_list, dry_run=dry_run)

def sed_delete_one(remove_string, filepath, dry_run=False):
    if not os.path.exists(filepath):
        raise Exception("Cannot remove line from non-existent file: %s" %
                filepath)
    cmd_list = ["/bin/sed", "-i", "/%s/d" % remove_string, filepath]
    run_command(cmd_list, dry_run=dry_run)

def sed_append(append_string, filepath, dry_run=False):
    if not os.path.exists(filepath):
        raise Exception("Cannot append line to non-existent file: %s" %
                filepath)
    if _line_exists_in_file(prepend_string, filepath):
        return
    cmd_list = ["/bin/sed", "-i", "$ a\\%s" % append_line, filepath]
    run_command(cmd_list, dry_run=dry_run)

def sed_prepend(prepend_string, filepath, dry_run=False):
    if not os.path.exists(filepath):
        raise Exception("Cannot prepend line to non-existent file: %s" %
                filepath)
    if _line_exists_in_file(prepend_string, filepath):
        return
    cmd_list = ["/bin/sed", "-i", "1i %s" % prepend_string, filepath]
    run_command(cmd_list, dry_run=dry_run)

def _line_exists_in_file(needle, filepath):
    with open(filepath,'r') as _file:
        if [line for line in _file.readlines()
            if needle == line]:
            return True
    return False

