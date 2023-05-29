import asyncio
import glob
import itertools
import json
import os
import sys
from typing import Any, Iterable, Optional, Collection

import bibtexparser
from bibtexparser.bparser import BibDatabase
from tqdm import tqdm

import config as cfg
import lookup_service as lus
import manual_reference_updater as mru
import output_processor as op
import utils as ut


def load_reference_bibliography(bibliography_dir: str) -> dict[str, list[str]]:
    """Loads a list of bibliographies from a list of files stored in a text file.

    Args:
        bibliography_dir (str): Path to the folder containing the bibliography files
            in the BibTeX format.

    Returns:
        dict[str, list[str]]: A dictionary mapping the id to its bibliography entry,
         line by line.
    """
    # Check if a cache.json file exists in the bibliography folder and if so, use this
    # one.
    cache_fn = os.path.join(bibliography_dir, "cache.json")
    filenames = glob.glob(os.path.join(bibliography_dir, "*.bib"))
    current_hashes = {os.path.basename(fn): ut.get_md5_hash(fn) for fn in filenames}
    if os.path.exists(cache_fn):
        with open(cache_fn, "r") as cache_f:
            cache = json.load(cache_f)

            # Check if the hashes of the current files are consistent with those used
            # to generate cache.json
            cache_hashes = cache["bib_hashes"]
            # If the hashes are consistent, return the cached bibliographies.
            if cache_hashes == current_hashes:
                print("Using cached pre-processed BibTex entries.")
                return cache["bibliographies"]
            # Otherwise, build new cache from scratch and overwrite the old one.

    bibliographies = {}
    bibparser = bibtexparser.bparser.BibTexParser(ignore_nonstandard_types=False)
    bibparser.expect_multiple_parse = True

    pbar = tqdm(filenames, desc="Parsing and preprocessing BibTeX files.")
    for fn in pbar:
        with open(fn, "r") as f:
            bibtexparser.load(f, bibparser)
            pbar.set_postfix_str(
                "Processed {0} entries.".format(len(bibparser.bib_database.entries))
            )

    for entry in bibparser.bib_database.entries:
        bibliographies[ut.cleanup_title(entry["title"])] = entry

    # Save the cache.
    with open(cache_fn, "w") as cache_f:
        json.dump(
            {"bib_hashes": current_hashes, "bibliographies": bibliographies}, cache_f
        )
    print("Saved pre-processed BibTex entries.")

    return bibliographies


def load_input_bibliography(input_fn: str) -> BibDatabase:
    """Loads the input bibliography from a bibtex file.

    Args:
        input_fn (str): The path to the input bibliography file.
    Returns:
        bibtexparser.bparser.BibDatabase: The input bibliography.
    """
    bibparser = bibtexparser.bparser.BibTexParser(ignore_nonstandard_types=False)
    with open(input_fn, "r") as input_f:
        return bibtexparser.load(input_f, bibparser).entries


def chunk_iterable(
    iterable: Iterable[Any], n: int, fillvalue: Any = None
) -> Iterable[list[Any]]:
    """Chunks an iterable into chunks of size n."""
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)


def process_bibliography_online(
    input_bibliography: list[dict[str, str]],
    config: cfg.OnlineUpdaterConfig,
    buffer_size: int = 15,
) -> list[op.BaseProcessingCommand]:
    n_parallel: int = config.n_parallel_requests

    print(config)
    lookup_services = []
    for service in list(set(config.services)):
        if service == "dblp":
            lookup_services.append(lus.DBLPLookupService())
        elif service == "crossref":
            lookup_services.append(lus.CrossrefLookupService())
        else:
            raise ValueError(f"Unknown service: {service}.")

    def get_reference_from_dict(entry: dict[str, str]) -> mru.Reference:
        return mru.Reference(
            int(entry.get("year", 0)),
            ut.cleanup_title(entry.get("title", "")),
            ut.cleanup_author(entry.get("author", "")),
            entry,
        )

    async def get_online_suggestions(entry: dict[str, str]) -> list[dict[str, str]]:
        suggestions = [lus.get_suggestions(entry, config.n_suggestions)
                       for lus in lookup_services]
        return list(
            itertools.chain(*await asyncio.gather(*suggestions))
        )

    async def get_reference_choice_task(
        entry: dict[str, str]
    ) -> mru.ReferenceChoiceTask:
        suggestions = await get_online_suggestions(entry)

        suggestions = [
            s for s in suggestions if "journal" not in s or s["journal"] != "CoRR"
        ]

        srs = [get_reference_from_dict(s) for s in suggestions]
        cr = get_reference_from_dict(entry)

        return mru.ReferenceChoiceTask(cr, srs)

    async def produce(queue: asyncio.Queue):
        # Add first rct separately to avoid waiting times at the beginning.
        for entry_chunks in chunk_iterable(input_bibliography[1:], n_parallel):
            rcts = await asyncio.gather(
                *[
                    get_reference_choice_task(entry)
                    for entry in entry_chunks
                    if entry is not None
                ]
            )
            for rct in rcts:
                await queue.put(rct)

        await queue.put(None)

    async def get_reference_choice_task_generator(queue: asyncio.Queue):
        while True:
            value = await queue.get()
            if value is None:
                break
            else:
                yield value

    queue: asyncio.Queue[mru.ReferenceChoiceTask] = asyncio.Queue(maxsize=buffer_size)
    mrfua = mru.ManualReferenceUpdaterApp(
        get_reference_choice_task_generator(queue), len(input_bibliography)
    )
    loop = asyncio.get_event_loop()
    loop.create_task(produce(queue))
    choices: Optional[list[mru.ReferenceChoice]] = mrfua.run()

    output_commands: list[op.BaseProcessingCommand] = []
    if choices is None:
        sys.exit()

    for rc in choices:
        if rc.current_reference == rc.chosen_reference:
            output_commands.append(
                op.KeepItemProcessingCommand(rc.current_reference.bibliography_values)
            )
        else:
            output_commands.append(
                op.UpdateItemProcessingCommand(
                    rc.current_reference.bibliography_values,
                    rc.chosen_reference.bibliography_values,
                    "manual",
                )
            )

    return output_commands


def process_bibliography_offline(
    input_bibliography: list[dict[str, str]],
    offline_bibliography: dict[str, dict[str, str]],
) -> list[op.BaseProcessingCommand]:
    """Processes the input bibliography offline.

    Args:
        input_bibliography (list[dict[str, str]]): The input bibliography.
        offline_bibliography (dict[str, dict[str, str]]): The reference
            bibliography items indexed by their normalized titles.

    Returns:
        list[op.BaseProcessingCommand]: The processing commands.
    """

    output_commands: list[op.BaseProcessingCommand] = []
    for ir in input_bibliography:
        mor = offline_bibliography.get(ut.cleanup_title(ir["title"]), None)
        if mor is None:
            output_commands.append(op.KeepItemProcessingCommand(ir))
        else:
            output_commands.append(op.UpdateItemProcessingCommand(ir, mor, "automated"))
    return output_commands


def main():
    config = cfg.get_config()
    reference_bibliography = load_reference_bibliography(config.bibliography_folder)
    input_bibliography = load_input_bibliography(config.input)
    processing_commands_offline = process_bibliography_offline(
        input_bibliography, reference_bibliography
    )
    update_processing_commands_offline = [
        pc
        for pc in processing_commands_offline
        if not isinstance(pc, op.KeepItemProcessingCommand)
    ]

    # Only update the bibliography online if no offline item has been found before.
    input_bibliography_online = [
        pc.current_item
        for pc in processing_commands_offline
        if isinstance(pc, op.KeepItemProcessingCommand)
    ]
    processing_commands_online = process_bibliography_online(
        input_bibliography_online, config.online_updater)

    processing_commands = (
        processing_commands_online + update_processing_commands_offline
    )

    op.write_output(op.process_commands(processing_commands), config.output)


if __name__ == "__main__":
    main()
