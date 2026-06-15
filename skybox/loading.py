import time
from contextlib import contextmanager

from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
)


@contextmanager
def loading_task(description: str):
    """
    Small terminal loading bar for operations with unknown duration.

    It advances artificially while the wrapped operation runs.
    This is cosmetic only; it does not affect the data pipeline.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=28),
        TimeElapsedColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task(description, total=100)

        progress.update(task, advance=8)
        time.sleep(0.05)

        try:
            yield
        finally:
            progress.update(task, completed=100)
            time.sleep(0.10)
