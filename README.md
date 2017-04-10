# atmosphere :cloud:


Atmosphere addresses the growing needs for highly configurable and customized computational resources to support research efforts in plant sciences. Atmosphere is an integrative, private, self-service cloud computing platform designed to provide easy access to preconfigured, frequently used analysis routines, relevant algorithms, and data sets in an available-on-demand environment designed to accommodate computationally and data-intensive bioinformatics tasks.

## Some Features

+ A powerful web client for management and administration of virtual machines
+ A fully RESTful API service for integrating with existing infrastructure components
+ Virtual machine images preconfigured for computational science and iPlant's infrastructure

## Running scripts

There are several utility scripts in `./scripts`. To run these:
```
cd <path to atmosphere>
export DJANGO_SETTINGS_MODULE='atmosphere.settings'
export PYTHONPATH="$PWD:$PYTHONPATH"
python scripts/<name of script>
```

## Contributing

### Coding Style
- Use 4 space indentation
- Limit lines to 79 characters
- Remove unused imports
- Remove trailing whitespace
- See [PEP8 - Style Guide for Python Code](https://www.python.org/dev/peps/pep-0008/)

It is recommended that you use the git `pre-commit` hook to ensure your code
is compliant with our style guide.

```bash
ln -s $(pwd)/contrib/pre-commit.hook $(pwd)/.git/hooks/pre-commit
```

To automate running tests before a push use the git `pre-push` hook to ensure
your code passes all the tests.

```bash
ln -s $(pwd)/contrib/pre-push.hook $(pwd).git/hooks/pre-push
```

When master is pulled, it's helpful to know if a `pip install` or a `manage.py
migrate` is necessary. To get other helpful warnings:
```bash
ln -s $(pwd)/contrib/post-merge.hook $(pwd)/.git/hooks/post-merge
```

### Coding Conventions

#### Import ordering
Imports should be grouped into the sections below and in sorted order.

1. Standard libraries
2. Third-party libraries
3. External project libraries
4. Local libraries

## License

See LICENSE.txt for license information

## Lead

+ **Edwin Skidmore <edwin@iplantcollaborative.org>**

## Authors 

The following individuals who have help/helped make :cloud: great appear in alphabetic order, by surname.

+ **Evan Briones <cloud-alum@iplantcollaborative.org>**
+ **Tharon Carlson <tharon@iplantcollaborative.org>**
+ **Joseph Garcia <cloud-alum@iplantcollaborative.org>**
+ **Steven Gregory <sgregory@iplantcollaborative.org>**
+ **Jason Hansen <cloud-alum@iplantcollaborative.org>**
+ **Christopher James LaRose <cloud-alum@iplantcollaborative.org>**
+ **Andrew Lenards <lenards@iplantcollaborative.org>**
+ **Monica Lent <cloud-alum@iplantcollaborative.org>**
+ **Andre Mercer <cloud-alum@iplantcollaborative.org>**
+ **J. Matt Peterson <cloud-alum@iplantcollaborative.org>**
+ **Julian Pistorius <julianp@iplantcollaborative.org>**

Where the cloud lives!
