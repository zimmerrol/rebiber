import abc
from datetime import datetime
from typing import Literal, Union


class BaseProcessingCommand(abc.ABC):
    """Base class for processing commands."""
    def __init__(self, current_item: dict[str, str]):
        self.current_item = current_item

    @property
    @abc.abstractmethod
    def output(self) -> dict[str, str]:
        pass


class UpdateItemProcessingCommand(BaseProcessingCommand):
    """A command to update an item in the bibliography.

    Args:
        current_item (dict[str, str]): The current item in the bibliography.
        new_item (dict[str, str]): The new item to replace the current item with.
    """
    def __init__(self, current_item: dict[str, str], new_item: dict[str, str],
                 method: Union[Literal["automated"], Literal["manual"]]):
        super().__init__(current_item)

        # Update id/key of the new item to match the current item.
        new_item["ID"] = current_item["ID"]

        current_date = datetime.now().strftime("%Y-%m-%d")
        new_item["eagerbib_comment"] = f"{method} update on {current_date}"

        self.new_item = new_item

    @property
    def output(self) -> dict[str, str]:
        return self.new_item


class KeepItemProcessingCommand(BaseProcessingCommand):
    """A command to keep an item in the bibliography.

    Args:
        current_item (dict[str, str]): The current item in the bibliography.
    """
    def __init__(self, current_item: dict[str, str]):
        super().__init__(current_item)

    @property
    def output(self) -> dict[str, str]:
        return self.current_item


def process_commands(commands: list[BaseProcessingCommand]) -> list[dict[str, str]]:
    """Process the commands and return the output bibliography items."""
    return [command.output for command in commands]


def write_output(output: list[dict[str, str]], output_fn: str) -> None:
    """Write the output to a file in BibTeX format.

    Args:
        output (list[dict[str, str]]): The output bibliography items to write.
        output_fn (str): The path to the output file.
    """
    all_lines = []
    for item in output:
        item_lines = [f"@{item['ENTRYTYPE']}{{{item['ID']},"]
        for key, value in item.items():
            if key == "ENTRYTYPE" or key == "ID":
                continue
            item_lines += [f"  {key} = {{{value}}},"]
        item_lines += ["}", ""]

        all_lines += item_lines

    # Remove the last newline.
    if len(all_lines) > 0:
        del all_lines[-1]

    with open(output_fn, "w") as f:
        f.write("\n".join(all_lines))
