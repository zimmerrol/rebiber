import asyncio
import itertools
import json
import os

import bibtexparser
from bibtexparser.bparser import BibDatabase
from tqdm import tqdm

import config as cfg
import lookup_service as lus
import manual_reference_updater as mru
import utils as ut


def load_reference_bibliography(
    bibliography_fns: str, base_dir: str = ""
) -> dict[str, list[str]]:
    """Loads a list of bibliographies from a list of files stored in a text file.

    Args:
        bibliography_fns (str): The path to the text file containing the list of
            bibliography files.
        base_dir (str, optional): The base directory to prepend to the filenames.

    Returns:
        dict[str, list[str]]: A dictionary mapping the id to its bibliography entry,
         line by line.
    """
    with open(bibliography_fns) as f:
        filenames = f.readlines()
    bibliographies = {}
    for filename in tqdm(filenames, leave=False, unit="bibliography"):
        with open(os.path.join(base_dir, filename.strip())) as f:
            db = json.load(f)
        bibliographies.update(db)
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


def update_input_bibliography_online(
    input_bibliography: list[dict[str, str]]
) -> list[dict[str, str]]:
    dblp_lookup_service = lus.DBLPLookupService()
    crossref_lookup_service = lus.CrossrefLookupService()

    def get_reference_from_dict(entry: dict[str, str]) -> mru.Reference:
        return mru.Reference(
            int(entry.get("year", 0)),
            ut.cleanup_title(entry.get("title", "")),
            ut.cleanup_author(entry.get("author", "")),
            entry,
        )

    async def def_get_online_suggestions(entry: dict[str, str]) -> list[dict[str, str]]:
        suggestions_dblp = dblp_lookup_service.get_suggestions(entry, 3)
        suggestions_cr = crossref_lookup_service.get_suggestions(entry, 3)
        return list(
            itertools.chain(*await asyncio.gather(suggestions_dblp, suggestions_cr))
        )

    async def produce(queue: asyncio.Queue):
        for idx, entry in enumerate(input_bibliography):
            suggestions = await def_get_online_suggestions(entry)

            suggestions = [
                s for s in suggestions if "journal" not in s or s["journal"] != "CoRR"
            ]

            srs = [get_reference_from_dict(s) for s in suggestions]
            cr = get_reference_from_dict(entry)

            await queue.put(mru.ReferenceChoiceTask(cr, srs))

        await queue.put(None)

    async def get_reference_choice_task_generator(queue: asyncio.Queue):
        while True:
            value = await queue.get()
            if value is None:
                break
            else:
                yield value

    queue = asyncio.Queue(maxsize=15)
    mrfua = mru.ManualReferenceUpdaterApp(get_reference_choice_task_generator(queue))
    loop = asyncio.get_event_loop()
    loop.create_task(produce(queue))
    choices = mrfua.run()

    return choices


def main():
    config = cfg.get_config()
    reference_bibliography = load_reference_bibliography(
        config.bibliographies, os.path.dirname(os.path.abspath(__file__))
    )

    input_bibliography = load_input_bibliography(config.input)
    update_input_bibliography_online(input_bibliography)


if __name__ == "__main__":
    main()
