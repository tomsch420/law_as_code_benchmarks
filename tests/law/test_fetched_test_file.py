"""
Tests of test files fetched from GitHub at a fixed commit.
"""

from __future__ import annotations

import io
from enum import StrEnum
from pathlib import Path

import pytest
from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.law.exceptions import UnfetchedTestFile
from law_as_code_benchmarks.law.fetched_test_file import FetchedTestFile

# %% a fetched test file


class ExampleTestFile(FetchedTestFile, StrEnum):
    """
    A benchmark's only fetched test file.
    """

    ONLY = "only.yaml"
    """
    The file.
    """

    @classproperty
    def repository(cls) -> str:
        return "owner/benchmark"

    @classproperty
    def revision(cls) -> str:
        return "0123abc"

    @classproperty
    def directory_in_repository(cls) -> str:
        return "tests"

    @classproperty
    def fetch_script(cls) -> str:
        return "scripts/fetch_example_tests.py"


@pytest.fixture
def fetched_to(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """:return: The directory the example's file is fetched to."""
    monkeypatch.setattr(
        ExampleTestFile, "path", property(lambda test_file: tmp_path / test_file.value)
    )
    return tmp_path


# %% downloading


def test_the_url_names_the_repository_revision_and_directory() -> None:
    """
    The file is read raw from GitHub at the revision.
    """
    assert ExampleTestFile.ONLY.url == (
        "https://raw.githubusercontent.com/owner/benchmark/0123abc/tests/only.yaml"
    )


def test_fetching_writes_what_the_url_serves(
    fetched_to: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    The download, mocked, lands at the file's path.
    """
    served = {ExampleTestFile.ONLY.url: b"- name: a test"}
    monkeypatch.setattr("urllib.request.urlopen", lambda url: io.BytesIO(served[url]))
    ExampleTestFile.ONLY.fetch()
    assert (fetched_to / ExampleTestFile.ONLY.value).read_bytes() == served[
        ExampleTestFile.ONLY.url
    ]


# %% missing files


def test_an_unfetched_file_is_refused(fetched_to: Path) -> None:
    """
    Nothing has been fetched to the directory.
    """
    with pytest.raises(UnfetchedTestFile):
        ExampleTestFile.ONLY.ensure_fetched()
