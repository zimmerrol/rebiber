import dataclasses
from typing import Optional, Callable

from textual.app import App, ComposeResult
from textual.containers import ScrollableContainer, Center
from textual.widgets import Button, Footer, Header, Static, Label, Placeholder
from textual.reactive import reactive
from textual import events
import random


@dataclasses.dataclass
class Reference:
    year: int
    title: str
    author: str


class ReferenceChoiceTask:
    def __init__(
        self, current_reference: Reference, available_references: list[Reference]
    ) -> None:
        if current_reference in available_references:
            available_references.remove(current_reference)
        available_references.insert(0, current_reference)
        self.current_reference = current_reference
        self.available_references = available_references


class YearTitleDisplay(Static):
    year: int = reactive(0)
    title: str = reactive("")
    __composed = False

    def __init__(self, year: int, title: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.year = year
        self.title = title

    def watch_year(self) -> None:
        if not self.__composed:
            return
        self.query_one("#year").update(str(self.year))

    def watch_title(self) -> None:
        if not self.__composed:
            return
        self.query_one("#title").update(self.title)

    def compose(self) -> ComposeResult:
        yield Label(str(self.year), id="year")
        yield Label(self.title, id="title")
        self.__composed = True


class ReferenceDisplay(Static):
    reference: Optional[Reference] = reactive(None)
    __composed = False
    can_focus = False
    can_focus_children = True

    def __init__(
        self,
        reference: Optional[Reference],
        clickable: bool = True,
        click_callback: Optional[Callable[[Reference], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.reference = reference
        self.clickable = clickable
        self.click_callback = click_callback

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.click_callback is not None:
            self.click_callback(self.reference)

    def compose(self) -> ComposeResult:
        year = self.reference.year if self.reference else 0
        title = self.reference.title if self.reference else ""
        author = self.reference.author if self.reference else ""
        yield YearTitleDisplay(year, title, id="yeartitle")
        yield Label(author, id="author")
        if self.clickable:
            yield Center(Button("Choose", id="choose"))
        self.__composed = True

    def watch_reference(self) -> None:
        if not self.__composed:
            return

        self.query_one("#yeartitle").year = self.reference.year
        self.query_one("#yeartitle").title = self.reference.title
        self.query_one("#author").update(self.reference.author)


class ReferencePicker(Static):
    available_references: list[Reference] = reactive([])
    current_reference: Reference = reactive(None)
    __composed = False
    focusable = True

    def __init__(
        self,
        get_next_choice_task_fn: Callable[[], ReferenceChoiceTask],
        get_choice_fn: Callable[[Reference], None],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.get_next_choice_task_fn = get_next_choice_task_fn
        self.get_choice_fn = get_choice_fn

    def _refresh_choice_task(self) -> None:
        print("refreshing choice task")
        choice_task = self.get_next_choice_task_fn()
        self.available_references = choice_task.available_references
        self.current_reference = choice_task.current_reference

    def _save_choice(self, reference: Reference) -> None:
        self.get_choice_fn(reference)
        self._refresh_choice_task()

    def compose(self) -> ComposeResult:
        yield ReferenceDisplay(None, clickable=False, id="current-reference")
        yield ScrollableContainer(
            *[
                ReferenceDisplay(rf, click_callback=self._save_choice)
                for rf in self.available_references
            ],
            id="available-references",
        )
        self.__composed = True

    def on_mount(self) -> None:
        self._refresh_choice_task()

    def watch_current_reference(self) -> None:
        if not self.__composed:
            return

        current = self.query_one("#current-reference")
        current.reference = self.current_reference

    def on_key(self, event: events.Key) -> None:
        if event.key in [str(d) for d in range(9)]:
            idx = int(event.key) - 1
            if 0 <= idx < len(self.available_references):
                rfd = self.query_one("#available-references").children[idx]
                button = rfd.query_one("#choose")
                if button.has_focus:
                    button.action_press()
                else:
                    button.focus(True)
        elif event.key == "up":
            rfds = self.query_one("#available-references").children
            current_idx = len(rfds)
            for idx, rfd in enumerate(rfds):
                if rfd.query_one("#choose").has_focus:
                    current_idx = idx
                    break
            rfds[(current_idx - 1) % len(rfds)].query_one("#choose").focus()
        elif event.key == "down":
            rfds = self.query_one("#available-references").children
            current_idx = -1
            for idx, rfd in enumerate(rfds):
                if rfd.query_one("#choose").has_focus:
                    current_idx = idx
                    break
            rfds[(current_idx + 1) % len(rfds)].query_one("#choose").focus()

    def watch_available_references(self) -> None:
        if not self.__composed:
            return

        references = self.query_one("#available-references")
        if references:
            while len(references.children) > 0:
                references.children[0].remove()

            for idx, rf in enumerate(self.available_references):
                rfd = ReferenceDisplay(rf, click_callback=self._save_choice)
                if idx > 0:
                    rfd.border_title = str(idx + 1)
                else:
                    # First element is the current reference; highlight it.
                    rfd.border_title = f"{idx + 1} (Current)"
                references.mount(rfd)


class ManualReferenceUpdaterApp(App):
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
    ]
    CSS_PATH = "tui.css"

    TITLE = "Reference Updater"

    def __init__(self):
        super().__init__()
        self.choice_tasks = self.load_choice_tasks()
        self.choices = []

    debug = True

    def load_choice_tasks(self) -> list[ReferenceChoiceTask]:
        return [
            ReferenceChoiceTask(
                Reference(2021, "0 Current Title" + str(random.random()), "An Author"),
                [
                    Reference(2021, "A Title" + str(random.random()), "An Author"),
                    Reference(2020, "Title" + str(random.random()), "Another Author"),
                    Reference(2021, "Title" + str(random.random()), "An Author"),
                    Reference(2020, "Title" + str(random.random()), "Another Author"),
                    Reference(2021, "itle" + str(random.random()), "An Author"),
                    Reference(2020, "Title" + str(random.random()), "Another Author"),
                ],
            )
            for _ in range(10)
        ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""

        def get_next_choice_task_fn() -> ReferenceChoiceTask:
            return self.choice_tasks.pop(0)

        def get_choice_fn(reference: Reference) -> None:
            self.choices.append(reference)

        yield Header()
        yield Footer()
        yield ReferencePicker(
            get_next_choice_task_fn, get_choice_fn, id="referencepicker"
        )

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_load_available_references(self) -> None:
        """An action to load demo references."""
        self.query_one(
            "#referencepicker"
        ).available_references = self.load_references()[0]

    def action_load_current_references(self) -> None:
        """An action to load demo references."""
        self.query_one("#referencepicker").current_reference = self.load_references()[1]


if __name__ == "__main__":
    app = ManualReferenceUpdaterApp()
    app.run()
