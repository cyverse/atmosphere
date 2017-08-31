import argparse

import django

django.setup()

from cyverse_allocation.tasks import renew_allocation_sources


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Print output rather than perform operation')
    parser.set_defaults(dry_run=False)
    args = parser.parse_args()
    renew_allocation_sources(renewal_strategy='default', ignore_current_compute_allowed=True, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
