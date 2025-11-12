"""Entry point for running keycloak as a module: python -m keycloak.cli"""

from .cli import main

if __name__ == '__main__':
    exit(main())
