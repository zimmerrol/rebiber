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


def process_commands(commands: list[BaseProcessingCommand],
                     sort: bool, deduplicate: bool) -> list[dict[str, str]]:
    """Process the commands and return the output bibliography items.

    Args:
        commands (list[BaseProcessingCommand]): The processing commands.
        sort (bool): Whether to sort the output bibliography items by their key.
        deduplicate (bool): Whether to deduplicate the output bibliography items.
    """
    entries = [command.output for command in commands]

    if sort:
        entries = sorted(entries, key=lambda x: x["ID"])

    if deduplicate:
        # Remove duplicate entries based on their ID.
        duplicated_idxs = []
        for i1 in range(len(entries)):
            for i2 in range(i1 + 1, len(entries)):
                if entries[i1]["ID"] == entries[i2]["ID"]:
                    duplicated_idxs.append(i2)
        for i in sorted(duplicated_idxs, reverse=True):
            del entries[i]

        # Remove duplicate entries based on their properties.
        duplicated_idx_pairs = []
        for i1 in range(len(entries)):
            l1 = transform_reference_dict_to_lines(entries[i1])
            s1 = "\n".join(l1[1:])
            for i2 in range(i1 + 1, len(entries)):
                l2 = transform_reference_dict_to_lines(entries[i2])
                s2 = "\n".join(l2[1:])
                if s1 == s2:
                    duplicated_idx_pairs.append((i1, i2))
        duplicated_idxs = sorted(duplicated_idx_pairs, key=lambda x: x[1], reverse=True)
        if len(duplicated_idxs) > 0:
            print("Detected duplicate entries:")
            for (i1, i2) in duplicated_idxs:
                print(f"• {entries[i2]['ID']} -> {entries[i1]['ID']}")
                del entries[i2]

    return entries


def transform_reference_dict_to_lines(item: dict[str, str]) -> list[str]:
    """Transform a reference dictionary to a list of lines."""
    item_lines = [f"@{item['ENTRYTYPE']}{{{item['ID']},"]
    for key, value in item.items():
        if key == "ENTRYTYPE" or key == "ID":
            continue
        item_lines += [f"  {key} = {{{value}}},"]
    item_lines += ["}"]
    return item_lines


def write_output(output: list[dict[str, str]], output_fn: str) -> None:
    """Write the output to a file in BibTeX format.

    Args:
        output (list[dict[str, str]]): The output bibliography items to write.
        output_fn (str): The path to the output file.
    """
    all_lines = []
    for item in output:
        all_lines += transform_reference_dict_to_lines(item) + [""]

    # Remove the last newline.
    if len(all_lines) > 0:
        del all_lines[-1]

    with open(output_fn, "w") as f:
        f.write("\n".join(all_lines))
