#!/usr/bin/env python
import argparse
import ConfigParser
import os
from pprint import pprint
import shutil

from jinja2 import Environment, FileSystemLoader, meta, StrictUndefined,\
    TemplateNotFound


# Configuration variables file path is relative to projectpath directory.
VARIABLES_FILENAME = 'variables.ini'


# Backup file extension.
BACKUP_EXT = '.bak'


config_files = {
    # semantic_name: (template_location, output_location)
    'apache': ('extras/apache/atmo.conf.j2', 'extras/apache/atmo.conf'),
    'local.py': ('atmosphere/settings/local.py.j2',
                 'atmosphere/settings/local.py'),
    'nginx': ('extras/nginx/Makefile.j2', 'extras/nginx/Makefile'),
    'nginx-site': ('extras/nginx/site.conf.j2',
                   'extras/nginx/site.conf'),
    'nginx-atmo': ('extras/nginx/locations/atmo.conf.j2',
                   'extras/nginx/locations/atmo.conf'),
    'nginx-flower': ('extras/nginx/locations/flower.conf.j2',
                     'extras/nginx/locations/flower.conf'),
    'nginx-jenkins': ('extras/nginx/locations/jenkins.conf.j2',
                      'extras/nginx/locations/jenkins.conf'),
    'nginx-lb': ('extras/nginx/locations/lb.conf.j2',
                 'extras/nginx/locations/lb.conf'),
    'secrets.py': ('atmosphere/settings/secrets.py.j2',
                   'atmosphere/settings/secrets.py')} 


projectpath = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))


loader = FileSystemLoader(projectpath)


env = Environment(loader=loader,
                  undefined=StrictUndefined)


variables_path = os.path.join(projectpath, VARIABLES_FILENAME)


def generate_new_key():
    import string, random
    new_key = ''.join(random.SystemRandom().choice(
        string.ascii_lowercase +
        string.digits +
        "!@#$%^&*(-_=+)") for _ in range(50))
    return new_key

def _get_variables():
    try:
        parser = ConfigParser.ConfigParser()
        parser.readfp(open(variables_path))
        variables = {}
        for section in parser.sections():
            # Ensure the variable names are upper case
            for option, value in parser.items(section):
                variables[option.upper()] = value
                if option.upper() == 'SECRET_KEY' and not value:
                    variables['SECRET_KEY'] = generate_new_key()
        return (variables, [])
    except Exception as e:
        return (False,
                ['Unable to get or parse '
                 'variables from %s' % (variables_path)])


def _get_filtered_config_files(configs):
    c_files = []
    messages = []
    success = True
    config_names = config_files.keys()
    if configs:
        for name in configs:
            if name in config_names:
                c_files.append(config_files[name])
            else:
                success = False
                messages.append('%s is not a valid key in'
                                ' config_files.' % (name))
        if not success:
            return (False, messages)
        return (c_files, [])
    else:
        return (config_files.values(), [])


def _handle_preconditions(configs):
    success = True
    c_files, messages = _get_filtered_config_files(configs)
    if not c_files:
        return (False, messages)
    variables, messages = _get_variables()
    if not variables:
        return (False, messages)
    for file_location, _ in c_files:
        try:
            file_path = os.path.join(projectpath,
                                     file_location)
            source = loader.get_source(env, file_location)
            ast = env.parse(loader.get_source(env, file_location))
            used_vars = meta.find_undeclared_variables(ast)
            ud_vars = set()
            for v in used_vars:
                if not v in variables:
                    ud_vars.add(v)
            if ud_vars:
                messages.append('Undeclared variables '
                                'found in %s: %s' % (file_path,
                                                     ud_vars))
                success = False
        except TemplateNotFound:
            messages.append('Template not found: %s' % (file_path))
            success = False
    return (success, messages)


def _backup_file(path):
    """
    Backup path if it's a file. Use the BACKUP_EXT extension.
    Return the backup location.
    """
    if os.path.isfile(path):
        shutil.copyfile(path, path + BACKUP_EXT)
        return path + BACKUP_EXT


def _generate_configs(configs, backup):
    success = True
    c_files, messages = _get_filtered_config_files(configs)
    if not c_files:
        return (False, messages)
    variables, messages = _get_variables()
    if not variables:
        return (False, messages)
    for template_location, output_location in c_files:
        try:
            output_path = os.path.join(projectpath,
                                       output_location)
            template = env.get_template(template_location)
            rendered = template.render(variables)
            if backup:
                backup_path = _backup_file(output_path)
                if backup_path:
                    messages.append('Backed up %s '\
                                    'as %s\n' % (output_location,
                                                 backup_path))
            # Write to the output file.
            with open(output_path, 'wb') as fh:
                fh.write(rendered)
            messages.append('From %s '\
                            'generated %s\n' % (template_location,
                                                output_location))
        except Exception as e:
            messages.append('Exception %s from template '\
                            'location %s and output location '\
                            '%s' % (e.message,
                                    template_location,
                                    output_location))
            success = False
    return (success, messages)


def generate_configs(configs, backup):
    print 'Testing for preconditions...\n'
    success, messages = _handle_preconditions(configs)
    print_messages(messages)
    if not success:
        exit(1)
    print 'Generating configs...\n'
    success, messages = _generate_configs(configs, backup)
    print_messages(messages)
    if not success:
        exit(2)


def print_messages(messages):
    for m in messages:
        print m


def print_configs(configs):
    """
    Print config name, template and output file information.
    """
    print 'Config Variables from %s' % (variables_path)
    variables, messages = _get_variables()
    if not variables:
        print_messages(messages)
    else:
        pprint(variables)
    print
    print 'Config Name:\n\tTemplate => Output'
    c_files, messages = _get_filtered_config_files(configs)
    if not c_files:
        print_messages(messages)
    for name in configs:
        template, output = config_files[name]
        print name + ':'
        print '\t %s => %s' % (template, output)
    print


def print_test(configs):
    """
    Print results of testing configs preconditions. If there are no
    problems acknowledge otherwise handle_precondition will print
    the error(s).
    """
    print 'Testing for preconditions...\n'
    c_files, messages = _get_filtered_config_files(configs)
    if not c_files:
        print_messages(messages)
        return
    for name in configs:
        success, messages = _handle_preconditions([name])
        if success:
            print '%s looks good.' % (name)
        else:
            print_messages(messages)
        print


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--show', action='store_true',
                        help='Show a list of availabe configs')
    parser.add_argument('-c', '--configs', nargs='*',
                        help='A list of configs to generate.')
    parser.add_argument('-b', '--backup', action='store_true',
                        help='Backup config output files before '
                        'generating new files.')
    parser.add_argument('-t', '--test', action='store_true',
                        help='Test configs for preconditions.')
    print 'Project Path => %s\n' % (projectpath)
    args = parser.parse_args()
    if not args.configs:
        args.configs = config_files.keys()
    if args.show:
        print_configs(args.configs)

    if args.test:
        print_test(args.configs)

    # If testing or showing information, exit.
    if args.test or args.show:
        exit(0)
    generate_configs(args.configs, args.backup)
    print 'Successfully generated configs %s.' % (', '.join(args.configs))
    exit(0)


if __name__ == '__main__':
    main()
