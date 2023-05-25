import dataclasses
import inspect
from typing import (Any, AsyncGenerator, Callable, Coroutine, Generator,
                    Optional, Union)

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Center, ScrollableContainer
from textual.reactive import Reactive, reactive
from textual.widgets import Button, Footer, Header, Label, Static


@dataclasses.dataclass
class Reference:
    year: int
    title: str
    author: str
    data: object


@dataclasses.dataclass
class ReferenceChoice:
    current_reference: Reference
    chosen_reference: Reference


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
    year: Reactive[int] = reactive(0)
    title: Reactive[str] = reactive("")
    __composed = False

    def __init__(self, year: int, title: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.year = year
        self.title = title

    def watch_year(self) -> None:
        if not self.__composed:
            return
        self.query_one("#year", expect_type=Label).update(str(self.year))

    def watch_title(self) -> None:
        if not self.__composed:
            return
        self.query_one("#title", expect_type=Label).update(self.title)

    def compose(self) -> ComposeResult:
        yield Label(str(self.year), id="year")
        yield Label(self.title, id="title")
        self.__composed = True


async def await_me_maybe(callback, *args, **kwargs):
    result = callback(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


async def anext_maybe(generator: Union[Generator, AsyncGenerator]) -> Optional[Any]:
    if hasattr(generator, "__anext__"):
        return await generator.__anext__()
    else:
        return next(generator)


class ReferenceDisplay(Static):
    reference: Reactive[Optional[Reference]] = reactive(None)
    __composed = False
    can_focus = False
    can_focus_children = True

    def __init__(
        self,
        reference: Optional[Reference],
        clickable: bool = True,
        click_callback: Optional[
            Callable[[Reference], Union[None, Coroutine[Any, Any, None]]]
        ] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.reference = reference
        self.clickable = clickable
        self.click_callback = click_callback

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.click_callback is not None:
            await await_me_maybe(self.click_callback, self.reference)

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

        if self.reference is None:
            return

        self.query_one("#yeartitle",
                       expect_type=YearTitleDisplay).year = self.reference.year
        self.query_one("#yeartitle",
                       expect_type=YearTitleDisplay).title = self.reference.title
        self.query_one("#author", expect_type=Label).update(self.reference.author)


class ReferencePicker(Static):
    available_references: Reactive[list[Reference]] = reactive([])
    current_reference: Reactive[Optional[Reference]] = reactive(None)
    __composed = False
    focusable = True

    def __init__(
        self,
        get_next_choice_task_fn: Callable[[], Optional[Union[
            ReferenceChoiceTask, Coroutine[Any, Any, Optional[ReferenceChoiceTask]]]]],
        get_choice_fn: Callable[[ReferenceChoice], None],
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.get_next_choice_task_fn = get_next_choice_task_fn
        self.get_choice_fn = get_choice_fn

    async def _refresh_choice_task(self) -> None:
        print("refreshing choice task")
        choice_task = await await_me_maybe(self.get_next_choice_task_fn)
        if choice_task is not None:
            self.available_references = choice_task.available_references
            self.current_reference = choice_task.current_reference

    async def _save_choice(self, reference: Reference) -> None:
        if self.current_reference is None:
            raise RuntimeError("No current reference to compare to.")

        self.get_choice_fn(ReferenceChoice(self.current_reference, reference))
        await await_me_maybe(self._refresh_choice_task)

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

    async def on_mount(self) -> None:
        await await_me_maybe(self._refresh_choice_task)

    def watch_current_reference(self) -> None:
        if not self.__composed:
            return

        current = self.query_one("#current-reference", expect_type=ReferenceDisplay)
        current.reference = self.current_reference

    def on_key(self, event: events.Key) -> None:
        if event.key in [str(d) for d in range(9)]:
            idx = int(event.key) - 1
            if 0 <= idx < len(self.available_references):
                rfd = self.query_one("#available-references").children[idx]
                button = rfd.query_one("#choose", expect_type=Button)
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
    CSS_PATH = "manual_reference_updater.css"

    TITLE = "Reference Updater"

    def __init__(
        self,
        choice_task_iterator: Union[
            Generator[ReferenceChoiceTask, None, None],
            AsyncGenerator[ReferenceChoiceTask, None],
        ],
    ):
        super().__init__()
        self.choice_task_iterator = choice_task_iterator
        self.choices: list[ReferenceChoice] = []

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""

        async def get_next_choice_task_fn() -> Optional[ReferenceChoiceTask]:
            try:
                choice_task = await anext_maybe(self.choice_task_iterator)
            except (StopAsyncIteration, StopIteration):
                self.exit(self.choices)
                return None
            else:
                return choice_task

        def get_choice_fn(reference_choice: ReferenceChoice) -> None:
            self.choices.append(reference_choice)

        yield Header()
        yield Footer()
        yield ReferencePicker(
            get_next_choice_task_fn, get_choice_fn, id="referencepicker"
        )

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark
