import click

from parm.envs.capstone import capstone_cli
from parm.envs.ida import ida_cli


@click.group()
def cli():
    pass

cli.add_command(capstone_cli)
cli.add_command(ida_cli)

if __name__ == '__main__':
    cli()
