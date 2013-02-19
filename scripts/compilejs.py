#!/usr/bin/env python
# Command line utility for compiling JS files into a single file for production environments
import os
from atmosphere import settings
from web.views import compile_js

def main():
    output_file_path = os.path.join(settings.root_dir, 'resources', 'js', 'cf2.min.js')
    output_file = open(output_file_path, 'w')

    compiled_js = compile_js()
    output_file.write(compiled_js)

if __name__ == "__main__":
    main()
