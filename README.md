## atmosphere
==========

Atmosphere addresses the growing needs for highly configurable and customized computational resources to support research efforts in plant sciences. Atmosphere is an integrative, private, self-service cloud computing platform designed to provide easy access to preconfigured, frequently used analysis routines, relevant algorithms, and data sets in an available-on-demand environment designed to accommodate computationally and data-intensive bioinformatics tasks.

## Some Features

+ A powerful web client for management and administration of virtual machines
+ A fully RESTful API service for integrating with existing infrastructure components
+ Virtual machine images preconfigured for computational science and iPlant's infrastructure

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
ln -s contrib/pre-commit.hook .git/hooks/pre-commit
```

To automate running tests before a push use the git `pre-push` hook to ensure
your code passes all the tests.

```bash
ln -s contrib/pre-push.hook .git/hooks/pre-push
```

### Coding Conventions

#### Import ordering
Imports should be grouped into the sections below and in sorted order.

1. Standard libraries
2. Third-party libraries
3. External project libraries
4. Local libraries

## License

See [LICENSE.txt](LICENSE.txt) for license information

## Lead

+ **Edwin Skidmore <edwin@iplantcollaborative.org>**

## Authors

+ **J. Matt Peterson <jmatt@iplantcollaborative.org>**
+ **Steven Gregory <sgregory@iplantcollaborative.org>**
+ **Andre Mercer <amercer@iplantcollaborative.org>**
+ **Evan Briones <evrick@iplantcollaborative.org>**
+ **Joseph Garcia <prosif@iplantcollaborative.org>**
+ **Monica Lent <mlent@iplantcollaborative.org>**
+ **Christopher James LaRose <cjlarose@iplantcollaborative.org>**
+ **Jason Hansen <jchansen@iplantcollaborative.org>**
+ **Tharon Carlson <tharon@iplantcollaborative.org>**

Where the cloud lives!
