from abc import ABC
from abc import abstractmethod
from typing import Dict
from typing import List
from typing import Union
import requests
import urllib
import re
import bibtexparser
import warnings


DictTree = Dict[str, Union[str, Dict[str, str]]]


class LookupService(ABC):
    @abstractmethod
    def get_suggestions(
        bib_entry: Dict[str, str], max_suggestions: int
    ) -> List[Dict[str, str]]:
        pass


class DBLPLookupService(LookupService):
    QUERY_TEMPLATE: str = "https://dblp.org/search/publ/api?format=bibtex&h={0}&q={1}"

    def get_suggestions(
        self, bib_entry: Dict[str, str], max_suggestions: int
    ) -> List[Dict[str, str]]:
        bibparser = bibtexparser.bparser.BibTexParser(ignore_nonstandard_types=False)

        normalized_title = urllib.parse.quote_plus(cleanup_title(bib_entry["title"]))
        request_url = DBLPLookupService.QUERY_TEMPLATE.format(
            max_suggestions, normalized_title
        )
        response = requests.get(request_url)
        if response.status_code == 200:
            response_data = response.text
            potential_items = bibtexparser.loads(response_data, bibparser).entries
            return potential_items
        else:
            warnings.warn(
                f"Unknown error occurred. Status code {response.status_code}."
            )
            return []


class CrossrefLookupService(LookupService):
    QUERY_TEMPLATE: str = "https://api.crossref.org/v1/works?rows={0}&query.title={1}"
    BIBTEX_QUERY_TEMPLATE: str = "https://api.crossref.org/v1/works/{0}/transform"

    def __load_bibtex(self, doi: str) -> None:
        bibparser = bibtexparser.bparser.BibTexParser(ignore_nonstandard_types=False)

        encoded_doi = urllib.parse.quote_plus(doi)
        request_url = CrossrefLookupService.BIBTEX_QUERY_TEMPLATE.format(encoded_doi)
        response = requests.get(
            request_url,
            headers={
                "Accept": "application/x-bibtex",
                "Accept-Encoding": "gzip, deflate, br",
            },
        )
        if response.status_code == 200:
            response_data = response.text
            return bibtexparser.loads(response_data, bibparser).entries[0]
        else:
            warnings.warn(
                f"Unknown error occurred. Status code {response.status_code}."
            )
            return None

    def get_suggestions(
        self, bib_entry: Dict[str, str], max_suggestions: int
    ) -> List[Dict[str, str]]:
        normalized_title = urllib.parse.quote_plus(cleanup_title(bib_entry["title"]))
        request_url = CrossrefLookupService.QUERY_TEMPLATE.format(
            max_suggestions, normalized_title
        )
        response = requests.get(request_url)
        if response.status_code == 200:
            response_data = response.json()
            raw_potential_items = response_data["message"]["items"]
            unique_dois = list(set([it["DOI"] for it in raw_potential_items]))
            potential_items = [self.__load_bibtex(doi) for doi in unique_dois]

            unique_dois = list(set([it["doi"] for it in potential_items]))

            used_dois = set()
            filtered_potential_items = []
            for pi in potential_items:
                if pi["doi"] in used_dois:
                    continue
                else:
                    used_dois.add(pi["doi"])
                    filtered_potential_items.append(pi)

            return filtered_potential_items
