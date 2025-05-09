from __future__ import annotations

from repository import gio
from utils_cy.levenshtein import compute_score
from utils.service import Service
from utils.logger import logger
from utils import Ref
from config import APP_CACHE_PATH, CACHE_PATH
from os.path import join as pjoin
import os.path as path
import json

apps = Ref[list["Application"]]([], name="applications", delayed_init=True)
frequents = Ref[dict[str, int]]({}, name="app_frequents", delayed_init=True)
FOUND_THRESHOLD = 0.4

APP_FREQUENCY = pjoin(APP_CACHE_PATH, "apps-frequency.json")
LEGACY_APP_FREQUENCY = pjoin(CACHE_PATH, "ags", "apps", "apps_frequency.json")


class Application:
    def __init__(
        self,
        app: gio.DesktopAppInfo
    ) -> None:
        self.app_info = app

        self.icon = app.get_string("Icon")
        self.exec = app.get_string("Exec")
        self.description = app.get_description()
        self.name = app.get_name()
        self.entry = app.get_id()
        self.keywords = app.get_keywords()
        self.frequency = 0
        self.score = 1

        self._match: dict[str | None, float] = {
            self.exec: -0.1,
            self.entry: -0.1,
            self.description: -0.2,
            self.name: 0.1
        }

    def launch(self) -> None:
        increase_frequency(self.entry)
        self.app_info.launch()

    def match(self, pattern: str) -> bool:
        scores = []

        normalized_pattern = pattern.strip().lower()

        for property, bonus in self._match.items():
            if property is None:
                continue

            normalized_property = property.lower()

            score = compute_score(normalized_property, normalized_pattern)
            score += bonus
            if score >= FOUND_THRESHOLD:
                self.score = score
                return True

            scores.append(score)

        if self.keywords:
            for keyword in self.keywords:
                if keyword is None:
                    continue

                normalized_keyword = keyword.lower()
                scores.append(
                    compute_score(normalized_keyword, normalized_pattern) - 1.5
                )

        self.score = max(scores) if scores else 0
        return self.score > FOUND_THRESHOLD


def increase_frequency(entry: str) -> None:
    if entry in frequents.value.keys():
        frequents.value[entry] += 1
    else:
        frequents.value[entry] = 1

    with open(APP_FREQUENCY, "w") as f:
        json.dump(frequents.value, f)


def get_apps_frequency() -> None:
    frequencies: dict[str, int] = {}
    for file_path in (APP_FREQUENCY, LEGACY_APP_FREQUENCY):
        if not path.exists(file_path):
            continue
        try:
            with open(file_path, "r") as f:
                parsed: dict[str, int] = json.load(f)
        except json.JSONDecodeError as e:
            logger.error("Couldn't read JSON file", exc_info=e)
            continue

        for key, frequency in parsed.items():
            if key in frequencies:
                frequencies[key] += frequency
            else:
                frequencies[key] = frequency

    return frequencies


def get_apps_list() -> list[Application]:
    apps = gio.AppInfo.get_all()
    new_list: list[Application] = []

    for app in apps:
        if not isinstance(app, gio.DesktopAppInfo):
            continue

        if app.get_nodisplay() or app.get_is_hidden() or not app.should_show():
            continue

        app = Application(app)
        app.frequency = frequents.value.get(app.entry, 0)
        new_list.append(app)

    return new_list


def reload() -> None:
    apps.value = get_apps_list()


class AppsService(Service):
    def app_init(self):
        frequents.value = get_apps_frequency()
        frequents.ready()

        reload()
        apps.ready()

    def start(self):
        ...

    def on_close(self):
        ...
