import rebiber
from rebiber.bib2json import load_bib_file
import argparse
import json
import bibtexparser
from bibtexparser.bwriter import BibTexWriter
import os
import re
from typing import Dict, List
import termcolor
import utils as ut

from rebiber.lookup_service import (
    DBLPLookupService,
    CrossrefLookupService,
)


def construct_bib_db(bib_list_fn: str, bib_base_dir: str = ""):
    """Constructs a bib database from a list of bib files stored in a text file."""
    with open(bib_list_fn) as f:
        filenames = f.readlines()
    bib_db = {}
    for filename in filenames:
        with open(os.path.join(bib_base_dir, filename.strip())) as f:
            db = json.load(f)
            print("Loaded:", f.name, "Size:", len(db))
        bib_db.update(db)
    return bib_db


def post_processing(output_bib_entries, removed_value_names, abbr_dict, sort: bool):
    bibparser = bibtexparser.bparser.BibTexParser(ignore_nonstandard_types=False)
    bib_entry_str = ""
    for entry in output_bib_entries:
        for line in entry:
            if ut.is_contain_var(line):
                continue
            bib_entry_str += line
        bib_entry_str += "\n"
    parsed_entries = bibtexparser.loads(bib_entry_str, bibparser)

    if len(parsed_entries.entries) < len(output_bib_entries) - 5:
        print(
            "Warning: len(parsed_entries.entries) < len(output_bib_entries) -5 -->",
            len(parsed_entries.entries),
            len(output_bib_entries),
        )
        output_str = ""
        for entry in output_bib_entries:
            for line in entry:
                output_str += line
            output_str += "\n"
        return output_str
    for output_entry in parsed_entries.entries:
        for remove_name in removed_value_names:
            if remove_name in output_entry:
                del output_entry[remove_name]
        for (short, pattern) in abbr_dict:
            for place in ["booktitle", "journal"]:
                if place in output_entry:
                    if re.match(pattern, output_entry[place]):
                        output_entry[place] = short

    writer = BibTexWriter()
    if not sort:
        writer.order_entries_by = None
    return bibtexparser.dumps(parsed_entries, writer=writer)


def get_online_selection(
    title: str, authors: str, year: int, suggestions: List[Dict[str, str]]
) -> Dict[str, str]:
    if len(suggestions) == 0:
        return None

    print(termcolor.colored("Multiple Potential Matches Found!", "yellow"))
    print(
        termcolor.colored("Original Title (Year): ", "green")
        + ut.cleanup_title(title)
        + (" (" + year + ")" if year is not None else "")
    )
    print(
        termcolor.colored("Original Authors:      ", "green")
        + authors.replace("\n", " ").replace("  ", "")
    )
    print()

    LINE_UP = "\033[1A"
    LINE_CLEAR = "\x1b[2K"

    for i, s in enumerate(suggestions):
        print(termcolor.colored(f"Option #{i}", "magenta"))
        print(
            termcolor.colored("• Title (Year):        ", "magenta")
            + ut.cleanup_title(s["title"])
            + (" (" + s["year"] + ")" if "year" in s else "")
        )
        if "author" in s:
            print(
                termcolor.colored("• Authors:             ", "magenta")
                + s["author"].replace("\n", " ").replace("  ", "")
            )
        else:
            print(termcolor.colored("• Authors:             ", "magenta"))
        print()

    def cleanup(attempts):
        n = len(suggestions) * 4 + 4 + attempts
        for _ in range(n):
            print(LINE_UP, end=LINE_CLEAR)

    attempts = 0
    while True:
        attempts += 1
        choice = input(
            "Enter either a number from 0 to "
            f"{len(suggestions) - 1} or n if no option is correct: "
        )
        if choice == "n":
            cleanup(attempts)
            return None
        elif choice.isdigit() and int(choice) < len(suggestions):
            cleanup(attempts)
            return suggestions[int(choice)]


def normalize_bib(
    bib_db,
    all_bib_entries,
    output_bib_path,
    deduplicate: bool = True,
    removed_value_names=[],
    abbr_dict=[],
    sort: bool = False,
    use_lookup_services: bool = False,
):
    if use_lookup_services:
        dblp_lookup_service = DBLPLookupService()
        crossref_lookup_service = CrossrefLookupService()
    output_bib_entries = []
    num_converted = 0
    bib_keys = set()

    def _proc_arxiv(bib_dict, original_bibkey, original_title):
        nonlocal num_converted
        bib_dict["arxiv_id"] = set()
        for match in re.finditer(
            r"(arxiv:|arxiv.org\/abs\/|arxiv.org\/pdf\/)([0-9]{4}).([0-9]{5})",
            bib_entry_str.lower(),
        ):
            bib_dict["arxiv_id"].add(f"{match.group(2)}.{match.group(3)}")

        if len(bib_dict["arxiv_id"]) == 1:
            bib_dict["arxiv_id"] = bib_dict["arxiv_id"].pop()
            bib_dict["arxiv_year"] = "20" + bib_dict["arxiv_id"].split(".")[0][:2]
            bib_entry = [
                line + "\n"
                for line in f"""@{bib_dict['ENTRYTYPE']}{{{bib_dict['ID']},
            title={{{bib_dict['title']}}},
            author={{{bib_dict['author']}}},
            journal={{ArXiv preprint}},
            volume={{abs/{bib_dict['arxiv_id']}}},
            year={{{bib_dict['arxiv_year']}}},
            url={{https://arxiv.org/abs/{bib_dict['arxiv_id']}}}
            }}""".split(
                    "\n"
                )
            ]

            log_str = "Normalized arXiv entry. ID: %s ; Title: %s" % (
                original_bibkey,
                original_title,
            )
            num_converted += 1
            print(log_str)

            return bib_entry

        return bib_dict

    for bib_entry in all_bib_entries:
        # read the title from this bib_entry
        bibparser = bibtexparser.bparser.BibTexParser(ignore_nonstandard_types=False)
        bib_entry_str = " ".join(
            [line for line in bib_entry if not ut.is_contain_var(line)]
        )
        bib_entry_parsed = bibtexparser.loads(bib_entry_str, bibparser)
        if (
            len(bib_entry_parsed.entries) == 0
            or "title" not in bib_entry_parsed.entries[0]
        ):
            continue
        original_title = bib_entry_parsed.entries[0]["title"]
        original_bibkey = bib_entry_parsed.entries[0]["ID"]
        if deduplicate and original_bibkey in bib_keys:
            continue
        bib_keys.add(original_bibkey)
        title = ut.cleanup_title(original_title)
        # try to map the bib_entry to the keys in all_bib_entries
        found_bibitem = None
        if title in bib_db and title:
            # update the bib_key to be the original_bib_key
            for line_idx in range(len(bib_db[title])):
                line = bib_db[title][line_idx]
                if line.strip().startswith("@"):
                    bibkey = line[line.find("{") + 1 : -1]
                    if not bibkey:
                        bibkey = bib_db[title][line_idx + 1].strip()[:-1]
                    line = line.replace(bibkey, original_bibkey + ",")
                    found_bibitem = bib_db[title].copy()
                    found_bibitem[line_idx] = line
                    break

            if found_bibitem is not None:
                log_str = "Converted. ID: %s ; Title: %s" % (
                    original_bibkey,
                    original_title.replace("\n", " ").replace("  ", " "),
                )
                num_converted += 1
                print(log_str)
                output_bib_entries.append(found_bibitem)
            else:
                raise RuntimeError("This should never happen.")
        else:
            bib_dict = bib_entry_parsed.entries[0]
            if use_lookup_services:
                suggestions_dblp = dblp_lookup_service.get_suggestions(bib_dict, 3)
                suggestions_cr = crossref_lookup_service.get_suggestions(bib_dict, 3)
                suggestions = suggestions_dblp + suggestions_cr

                suggestions = [
                    s
                    for s in suggestions
                    if "journal" not in s or s["journal"] != "CoRR"
                ]

                choice = get_online_selection(
                    bib_dict["title"],
                    bib_dict["author"],
                    bib_dict.get("year", None),
                    suggestions,
                )

                if choice is None:
                    output_bib_entries.append(
                        _proc_arxiv(bib_dict, original_bibkey, original_title)
                    )
                else:
                    bib_entry = [f"@{choice['ENTRYTYPE']}{{{bib_dict['ID']},\n"]
                    for key, value in choice.items():
                        if key == "ENTRYTYPE" or key == "ID":
                            continue
                        bib_entry += [f" {key} = {{{value}}},\n"]
                    bib_entry += ["}\n"]

                    log_str = "Converted online entry. ID: %s ; Title: %s" % (
                        original_bibkey,
                        original_title,
                    )
                    num_converted += 1
                    print(log_str)
                    output_bib_entries.append(bib_entry)
            else:
                output_bib_entries.append(
                    _proc_arxiv(bib_dict, original_bibkey, original_title)
                )

    print("Num of converted items:", num_converted)
    # post-formatting
    output_string = post_processing(
        output_bib_entries, removed_value_names, abbr_dict, sort
    )
    with open(output_bib_path, "w", encoding="utf8") as output_file:
        output_file.write(output_string)
    print("Written to:", output_bib_path)


def load_abbr_tsv(abbr_tsv_file):
    abbr_dict = []
    with open(abbr_tsv_file) as f:
        for line in f.read().splitlines():
            ls = line.split("|")
            if len(ls) == 2:
                abbr_dict.append((ls[0].strip(), ls[1].strip()))
    return abbr_dict


def main():
    filepath = os.path.dirname(os.path.abspath(__file__)) + "/"
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--version", action="store_true", help="Print the version of Rebiber."
    )
    parser.add_argument("-i", "--input_bib", type=str, help="The input bib file")
    parser.add_argument(
        "-o", "--output_bib", default="same", type=str, help="The output bib file"
    )
    parser.add_argument(
        "-l",
        "--bib_list",
        default=filepath + "bib_list.txt",
        type=str,
        help="The list of candidate bib data.",
    )
    parser.add_argument(
        "-a",
        "--abbr_tsv",
        default=filepath + "abbr.tsv",
        type=str,
        help="The list of conference abbreviation data.",
    )
    parser.add_argument(
        "-d",
        "--deduplicate",
        default=True,
        type=bool,
        help="True to remove entries with duplicate keys.",
    )
    parser.add_argument(
        "-s",
        "--shorten",
        default=False,
        type=bool,
        help="True to shorten the conference names.",
    )
    parser.add_argument(
        "-r",
        "--remove",
        default="",
        type=str,
        help="A comma-seperated list of values you want to remove, "
             "such as '--remove url,biburl,address,publisher'.",
    )
    parser.add_argument(
        "-st",
        "--sort",
        default=False,
        type=bool,
        help="True to sort the output BibTeX entries alphabetically by ID",
    )
    parser.add_argument(
        "-ol",
        "--online",
        action="store_true",
        help="True to use online resources to look for missing BibTeX "
             "entries in a semi-automated way.",
    )
    args = parser.parse_args()

    if args.version:
        print(rebiber.__version__)
        return

    assert args.input_bib is not None, "You need to specify an input path by -i xxx.bib"
    bib_db = construct_bib_db(args.bib_list, start_dir=filepath)
    all_bib_entries = load_bib_file(args.input_bib)
    output_path = args.input_bib if args.output_bib == "same" else args.output_bib
    removed_value_names = [s.strip() for s in args.remove.split(",")]
    if args.shorten:
        abbr_dict = load_abbr_tsv(args.abbr_tsv)
    else:
        abbr_dict = []

    normalize_bib(
        bib_db,
        all_bib_entries,
        output_path,
        args.deduplicate,
        removed_value_names,
        abbr_dict,
        args.sort,
        args.online,
    )


if __name__ == "__main__":
    main()
