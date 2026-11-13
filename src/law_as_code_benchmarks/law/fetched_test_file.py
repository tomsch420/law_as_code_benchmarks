"""
Test files a script fetches from a benchmark's GitHub repository at a fixed commit,
because their licence keeps them out of this repository.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

from krrood.ormatic.utils import classproperty

from law_as_code_benchmarks.law.exceptions import UnfetchedTestFile

# %% fetched test files


class FetchedTestFile:
    """
    A test file fetched from GitHub, mixed into a benchmark's enumeration of such files,
    each member's value the file's name.
    """

    @classproperty
    def repository(cls) -> str:
        """
        The GitHub repository holding the files, as ``owner/name``.
        """
        raise NotImplementedError

    @classproperty
    def revision(cls) -> str:
        """
        The commit the files are fetched at.
        """
        raise NotImplementedError

    @classproperty
    def directory_in_repository(cls) -> str:
        """
        The directory of the repository holding the files.
        """
        raise NotImplementedError

    @classproperty
    def fetch_script(cls) -> str:
        """
        The script fetching the files, relative to the repository's root.
        """
        raise NotImplementedError

    @property
    def path(self) -> Path:
        """
        Where the file is fetched to.
        """
        raise NotImplementedError

    @property
    def url(self) -> str:
        """
        Where the file is downloaded from.
        """
        return (
            f"https://raw.githubusercontent.com/{self.repository}/{self.revision}/"
            f"{self.directory_in_repository}/{self.value}"
        )

    def fetch(self) -> None:
        """
        Downloads the file to :attr:`path`.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(self.url) as response:
            self.path.write_bytes(response.read())

    def ensure_fetched(self) -> None:
        """
        :raises UnfetchedTestFile: Where the file has not been fetched.
        """
        if not self.path.exists():
            raise UnfetchedTestFile(
                file_name=self.value, fetch_script=self.fetch_script
            )
