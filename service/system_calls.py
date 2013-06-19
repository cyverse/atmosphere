"""
System calls that get used all the time..
"""
import subprocess

def run_command(commandList, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                stdin=None, dry_run=False):
    """
    NOTE: Use this to run ANY system command, because its wrapped around a loggger
    Using Popen, run any command at the system level and record the output and error streams
    """
    out = None
    err = None
    logger.debug("Command:<%s>" % ' '.join(commandList))
    if dry_run:
        #Bail before making the call
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
        logger.debug("STDIN: %s" % stdin)
    logger.debug("STDOUT: %s" % out)
    logger.debug("STDERR: %s" % err)
    return (out,err)


def overwrite_file(filepath, dry_run=False):
    if not os.path.exists(filepath):
        raise Exception("Cannot remove lines from non-existent file: %s" %
                filepath)
    cmd_list = ['/bin/cp', '-f', '/dev/null', '%s' % filepath]
    if dry_run:
        logger.info(cmd_list)
        return
    run_command(cmd_list)


def wildcard_remove(self, wildcard_path, dry_run=False):
    """
    Expand the wildcard to match all files, delete each one.
    """
    logger.debug(wildcard_path)
    glob_list = glob.glob(wildcard_path)
    if glob_list:
        for filename in glob_list:
            cmd_list = ['/bin/rm', '-rf', filename]
            if dry_run:
                logger.info(cmd_list)
                continue
            run_command(cmd_list)

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
    if dry_run:
        logger.info(cmd_list)
        return
    run_command(cmd_list)

def sed_replace(find,replace,filepath, dry_run=False):
    if not os.path.exists(filepath):
        raise Exception("Cannot replace line from non-existent file: %s" %
                filepath)
    cmd_list = ["/bin/sed", "-i", "s/%s/%s/" % (find,replace), filepath]
    if dry_run:
        logger.info(cmd_list)
        return
    run_command(cmd_list)

def sed_delete_one(remove_string, filepath, dry_run=False):
    if not os.path.exists(filepath):
        raise Exception("Cannot remove line from non-existent file: %s" %
                filepath)
    cmd_list = ["/bin/sed", "-i", "/%s/d" % remove_string, filepath]
    if dry_run:
        logger.info(cmd_list)
        return
    run_command(cmd_list)

def sed_append(append_string, filepath, dry_run=False):
    if not os.path.exists(filepath):
        raise Exception("Cannot append line to non-existent file: %s" %
                filepath)
    if _line_exists_in_file(prepend_string, filepath):
        return
    cmd_list = ["/bin/sed", "-i", "$ a\\%s" % append_line, filepath]
    if dry_run:
        logger.info(cmd_list)
        return
    run_command(cmd_list)

def sed_prepend(prepend_string, filepath, dry_run=False):
    if not os.path.exists(filepath):
        raise Exception("Cannot prepend line to non-existent file: %s" %
                filepath)
    if _line_exists_in_file(prepend_string, filepath):
        return
    cmd_list = ["/bin/sed", "-i", "1i %s" % prepend_string, filepath]
    if dry_run:
        logger.info(cmd_list)
        return
    run_command(cmd_list)

def _line_exists_in_file(needle, filepath):
    with open(filepath,'r') as _file:
        if [line for line in _file.readlines()
            if needle == line]:
            return True
    return False

