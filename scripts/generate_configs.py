#!/usr/bin/env python
import os

from jinja2 import Environment, FileSystemLoader, meta, StrictUndefined,\
    TemplateNotFound


config_files = {
    # semantic_name: (template_location, output_location)
    'nginx': ('extras/nginx/Makefile.j2', 'extras/nginx/Makefile'),
    'apache': ('extras/apache/atmo.conf.j2', 'extras/apache/atmo.conf'),
    'local': ('atmosphere/settings/local.py.j2',
              'atmosphere/settings/local.py')}


projectpath = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))


loader = FileSystemLoader(projectpath)


env = Environment(loader=loader,
                  undefined=StrictUndefined)


context = {}


def handle_preconditions():
    return True
    success = True
    for file_location, _ in config_files.values():
        try:
            file_path = os.path.join(projectpath,
                                     file_location)
            source = loader.get_source(env, file_location)
            ast = env.parse(loader.get_source(env, file_location))
            ud_vars = meta.find_undeclared_variables(ast)
            if ud_vars:
                print 'Undeclared variables found in %s: %s' % (file_path,
                                                                ud_vars)
                success = False
        except TemplateNotFound:
            print 'Template not found: %s' % (file_path)
            success = False
    return success


def generate_configs():
    success = True
    for template_location, output_location in config_files.values():
        try:
            output_path = os.path.join(projectpath,
                                       output_location)
            template = env.get_template(template_location)
            rendered = template.render(context)
            with open(output_path, 'wb') as fh:
                fh.write(rendered)
            print 'From %s '\
                'generated %s' % (template_location, output_location)
        except Exception as e:
            print 'Exception %s from template '\
                'location %s and output location '\
                '%s' % (e.message, template_location, output_location)
            success = False
    return success


def main():
    i = 1
    for step in [handle_preconditions, generate_configs]:
        success = step()
        if not success:
            exit(i)
        i += 1
    exit(0)


if __name__ == '__main__':
    main()
