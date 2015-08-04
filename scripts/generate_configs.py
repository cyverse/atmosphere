#!/usr/bin/env python
import os

from jinja2 import Environment, FileSystemLoader, meta, StrictUndefined,\
    TemplateNotFound


config_files = {
    'nginx': 'extras/nginx/Makefile.j2',
    'apache': 'extras/apache/atmo.conf.j2',
    'local': 'atmosphere/settings/local.py.j2'}


projectpath = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))


loader = FileSystemLoader(projectpath)


env = Environment(loader=loader,
                  undefined=StrictUndefined)


def handle_preconditions():
    result = True
    for file_location in config_files.values():
        try:
            file_path = os.path.join(projectpath,
                                     file_location)
            source = loader.get_source(env, file_location)
            ast = env.parse(loader.get_source(env, file_location))
            ud_vars = meta.find_undeclared_variables(ast)
            if ud_vars:
                print 'Undeclared variables found in %s: %s' % (file_path,
                                                                ud_vars)
                result = False
        except TemplateNotFound:
            print 'Template not found: %s' % (file_path)
            result = False
    return result


def main():
    if not handle_preconditions():
        exit(1)


if __name__ == '__main__':
    main()
