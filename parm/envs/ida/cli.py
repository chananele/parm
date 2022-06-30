import click

from parm.resources import get_asciiart

@click.group(name="ida")
def cli():
    click.echo(get_asciiart(color=True), color=True)
    raise NotImplementedError()
