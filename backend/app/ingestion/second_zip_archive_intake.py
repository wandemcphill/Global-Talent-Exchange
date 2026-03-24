from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import csv
from dataclasses import dataclass
from io import TextIOWrapper
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from zipfile import BadZipFile, ZipFile, ZipInfo

REQUIRED_SECOND_ZIP_DATASETS = (
    "players.csv",
    "clubs.csv",
    "competitions.csv",
    "countries.csv",
    "national_teams.csv",
    "player_valuations.csv",
    "transfers.csv",
    "club_games.csv",
)
_REQUIRED_DATASET_LOOKUP = {
    dataset_name.casefold(): dataset_name for dataset_name in REQUIRED_SECOND_ZIP_DATASETS
}


class SecondZipArchiveIntakeError(ValueError):
    pass


class SecondZipArchiveValidationError(SecondZipArchiveIntakeError):
    pass


class SecondZipArchiveMalformedError(SecondZipArchiveIntakeError):
    pass


@dataclass(frozen=True, slots=True)
class SecondZipArchiveFileMetadata:
    dataset_name: str
    archive_name: str
    is_required: bool
    file_size_bytes: int
    compressed_size_bytes: int
    column_names: tuple[str, ...] = ()
    row_count: int | None = None


@dataclass(frozen=True, slots=True)
class SecondZipArchiveInspection:
    archive_path: Path
    entries: tuple[SecondZipArchiveFileMetadata, ...]
    required_files: tuple[str, ...]
    missing_files: tuple[str, ...]
    unexpected_files: tuple[str, ...]
    total_file_size_bytes: int
    total_compressed_size_bytes: int

    @property
    def is_complete(self) -> bool:
        return not self.missing_files

    def get_entry(self, dataset_name: str) -> SecondZipArchiveFileMetadata | None:
        canonical_name = dataset_name.casefold()
        for entry in self.entries:
            if entry.dataset_name.casefold() == canonical_name:
                return entry
        return None


@dataclass(frozen=True, slots=True)
class ExtractedSecondZipArchive:
    archive_path: Path
    workdir: Path
    inspection: SecondZipArchiveInspection
    extracted_files: dict[str, Path]

    def get_path(self, dataset_name: str) -> Path:
        canonical_name = _canonical_required_dataset_name(dataset_name)
        try:
            return self.extracted_files[canonical_name]
        except KeyError as exc:
            raise KeyError(f"Dataset '{canonical_name}' was not extracted.") from exc


@dataclass(frozen=True, slots=True)
class _SecondZipMember:
    dataset_name: str
    archive_name: str
    info: ZipInfo
    is_required: bool


@dataclass(slots=True)
class SecondZipArchiveIntakeService:
    temp_root: Path | None = None
    temp_prefix: str = "gtex-2ndzip-"
    csv_encoding: str = "utf-8-sig"
    max_member_count: int = 32
    max_file_size_bytes: int = 256 * 1024 * 1024
    max_total_size_bytes: int = 512 * 1024 * 1024

    def inspect_archive(
        self,
        archive_path: str | Path,
        *,
        include_row_counts: bool = False,
    ) -> SecondZipArchiveInspection:
        resolved_path = self._resolve_archive_path(archive_path)
        try:
            with ZipFile(resolved_path) as archive:
                members = self._load_members(archive)
                metadata_by_dataset: dict[str, tuple[tuple[str, ...], int | None]] = {}
                for member in members:
                    if member.is_required:
                        metadata_by_dataset[member.dataset_name] = self._inspect_required_member(
                            archive,
                            member,
                            include_row_counts=include_row_counts,
                        )

                entries = tuple(
                    SecondZipArchiveFileMetadata(
                        dataset_name=member.dataset_name,
                        archive_name=member.archive_name,
                        is_required=member.is_required,
                        file_size_bytes=member.info.file_size,
                        compressed_size_bytes=member.info.compress_size,
                        column_names=metadata_by_dataset.get(member.dataset_name, ((), None))[0],
                        row_count=metadata_by_dataset.get(member.dataset_name, ((), None))[1],
                    )
                    for member in members
                )
        except FileNotFoundError as exc:
            raise SecondZipArchiveValidationError(f"Archive '{resolved_path}' was not found.") from exc
        except BadZipFile as exc:
            raise SecondZipArchiveMalformedError(
                f"Archive '{resolved_path.name}' is not a readable zip file."
            ) from exc
        except OSError as exc:
            raise SecondZipArchiveValidationError(
                f"Archive '{resolved_path.name}' could not be opened: {exc}."
            ) from exc

        present_required = {entry.dataset_name for entry in entries if entry.is_required}
        missing_files = tuple(
            dataset_name
            for dataset_name in REQUIRED_SECOND_ZIP_DATASETS
            if dataset_name not in present_required
        )
        unexpected_files = tuple(
            entry.dataset_name for entry in entries if not entry.is_required
        )
        return SecondZipArchiveInspection(
            archive_path=resolved_path,
            entries=entries,
            required_files=REQUIRED_SECOND_ZIP_DATASETS,
            missing_files=missing_files,
            unexpected_files=unexpected_files,
            total_file_size_bytes=sum(entry.file_size_bytes for entry in entries),
            total_compressed_size_bytes=sum(entry.compressed_size_bytes for entry in entries),
        )

    def validate_archive(self, archive_path: str | Path) -> SecondZipArchiveInspection:
        inspection = self.inspect_archive(archive_path, include_row_counts=True)
        if inspection.missing_files:
            missing_files = ", ".join(inspection.missing_files)
            raise SecondZipArchiveValidationError(
                f"Archive '{inspection.archive_path.name}' is missing required dataset files: {missing_files}."
            )
        return inspection

    @contextmanager
    def open_csv_rows(
        self,
        archive_path: str | Path,
        dataset_name: str,
    ) -> Iterator[csv.DictReader]:
        canonical_name = _canonical_required_dataset_name(dataset_name)
        resolved_path = self._resolve_archive_path(archive_path)
        try:
            with ZipFile(resolved_path) as archive:
                members_by_dataset = {
                    member.dataset_name: member for member in self._load_members(archive)
                }
                missing_files = tuple(
                    required_name
                    for required_name in REQUIRED_SECOND_ZIP_DATASETS
                    if required_name not in members_by_dataset
                )
                if missing_files:
                    missing_list = ", ".join(missing_files)
                    raise SecondZipArchiveValidationError(
                        f"Archive '{resolved_path.name}' is missing required dataset files: {missing_list}."
                    )

                member = members_by_dataset[canonical_name]
                with archive.open(member.info, mode="r") as raw_handle:
                    with TextIOWrapper(
                        raw_handle,
                        encoding=self.csv_encoding,
                        newline="",
                    ) as text_handle:
                        reader = csv.DictReader(text_handle)
                        field_names = tuple(reader.fieldnames or ())
                        if not field_names or not any(str(name).strip() for name in field_names):
                            raise SecondZipArchiveValidationError(
                                f"Dataset '{canonical_name}' is missing a header row."
                            )
                        try:
                            yield reader
                        except UnicodeDecodeError as exc:
                            raise SecondZipArchiveValidationError(
                                f"Dataset '{canonical_name}' is not valid UTF-8 text."
                            ) from exc
                        except csv.Error as exc:
                            raise SecondZipArchiveValidationError(
                                f"Dataset '{canonical_name}' is malformed CSV: {exc}."
                            ) from exc
                        except BadZipFile as exc:
                            raise SecondZipArchiveMalformedError(
                                f"Archive '{resolved_path.name}' became unreadable while streaming "
                                f"'{canonical_name}'."
                            ) from exc
        except FileNotFoundError as exc:
            raise SecondZipArchiveValidationError(f"Archive '{resolved_path}' was not found.") from exc
        except BadZipFile as exc:
            raise SecondZipArchiveMalformedError(
                f"Archive '{resolved_path.name}' is not a readable zip file."
            ) from exc

    @contextmanager
    def extract_archive(
        self,
        archive_path: str | Path,
    ) -> Iterator[ExtractedSecondZipArchive]:
        inspection = self.validate_archive(archive_path)
        temp_root = self.temp_root
        if temp_root is not None:
            temp_root.mkdir(parents=True, exist_ok=True)
        workdir = Path(tempfile.mkdtemp(prefix=self.temp_prefix, dir=temp_root))
        extracted_files: dict[str, Path] = {}
        try:
            with ZipFile(inspection.archive_path) as archive:
                members_by_dataset = {
                    member.dataset_name: member for member in self._load_members(archive)
                }
                for dataset_name in REQUIRED_SECOND_ZIP_DATASETS:
                    member = members_by_dataset[dataset_name]
                    destination = workdir / dataset_name
                    with archive.open(member.info, mode="r") as source, destination.open("wb") as target:
                        shutil.copyfileobj(source, target)
                    extracted_files[dataset_name] = destination

            yield ExtractedSecondZipArchive(
                archive_path=inspection.archive_path,
                workdir=workdir,
                inspection=inspection,
                extracted_files=extracted_files,
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def _resolve_archive_path(self, archive_path: str | Path) -> Path:
        return Path(archive_path).expanduser().resolve()

    def _load_members(self, archive: ZipFile) -> tuple[_SecondZipMember, ...]:
        infos = archive.infolist()
        if not infos:
            raise SecondZipArchiveValidationError("Archive is empty.")
        if len(infos) > self.max_member_count:
            raise SecondZipArchiveValidationError(
                f"Archive contains {len(infos)} entries; expected at most {self.max_member_count}."
            )

        total_file_size = 0
        seen_dataset_names: set[str] = set()
        members: list[_SecondZipMember] = []
        for info in infos:
            member = self._coerce_member(info)
            total_file_size += info.file_size
            if info.file_size > self.max_file_size_bytes:
                raise SecondZipArchiveValidationError(
                    f"Archive entry '{member.archive_name}' exceeds the {self.max_file_size_bytes} byte limit."
                )
            if total_file_size > self.max_total_size_bytes:
                raise SecondZipArchiveValidationError(
                    f"Archive exceeds the {self.max_total_size_bytes} byte total size limit."
                )
            dataset_key = member.dataset_name.casefold()
            if dataset_key in seen_dataset_names:
                raise SecondZipArchiveValidationError(
                    f"Archive contains duplicate top-level file '{member.dataset_name}'."
                )
            seen_dataset_names.add(dataset_key)
            members.append(member)
        return tuple(members)

    def _coerce_member(self, info: ZipInfo) -> _SecondZipMember:
        archive_name = info.filename.replace("\\", "/").strip()
        if not archive_name:
            raise SecondZipArchiveMalformedError("Archive contains an unnamed entry.")
        if info.is_dir():
            raise SecondZipArchiveMalformedError(
                f"Archive entry '{archive_name}' must be a file, not a directory."
            )

        entry_path = PurePosixPath(archive_name)
        if entry_path.is_absolute() or len(entry_path.parts) != 1:
            raise SecondZipArchiveMalformedError(
                f"Archive entry '{archive_name}' must be a top-level file."
            )
        if any(part in {"", ".", ".."} for part in entry_path.parts):
            raise SecondZipArchiveMalformedError(
                f"Archive entry '{archive_name}' contains an unsafe path."
            )

        required_name = _REQUIRED_DATASET_LOOKUP.get(entry_path.name.casefold())
        dataset_name = required_name or entry_path.name
        return _SecondZipMember(
            dataset_name=dataset_name,
            archive_name=archive_name,
            info=info,
            is_required=required_name is not None,
        )

    def _inspect_required_member(
        self,
        archive: ZipFile,
        member: _SecondZipMember,
        *,
        include_row_counts: bool,
    ) -> tuple[tuple[str, ...], int | None]:
        try:
            with archive.open(member.info, mode="r") as raw_handle:
                with TextIOWrapper(
                    raw_handle,
                    encoding=self.csv_encoding,
                    newline="",
                ) as text_handle:
                    reader = csv.reader(text_handle)
                    header = next(reader, None)
                    if header is None:
                        raise SecondZipArchiveValidationError(
                            f"Dataset '{member.dataset_name}' is empty."
                        )
                    column_names = tuple(str(value).strip() for value in header)
                    if not any(column_names):
                        raise SecondZipArchiveValidationError(
                            f"Dataset '{member.dataset_name}' is missing a header row."
                        )

                    row_count: int | None = None
                    if include_row_counts:
                        row_count = sum(1 for _ in reader)
                    return column_names, row_count
        except UnicodeDecodeError as exc:
            raise SecondZipArchiveValidationError(
                f"Dataset '{member.dataset_name}' is not valid UTF-8 text."
            ) from exc
        except csv.Error as exc:
            raise SecondZipArchiveValidationError(
                f"Dataset '{member.dataset_name}' is malformed CSV: {exc}."
            ) from exc
        except BadZipFile as exc:
            raise SecondZipArchiveMalformedError(
                f"Archive '{Path(archive.filename or '').name}' became unreadable while validating "
                f"'{member.archive_name}'."
            ) from exc


def _canonical_required_dataset_name(dataset_name: str) -> str:
    try:
        return _REQUIRED_DATASET_LOOKUP[dataset_name.casefold()]
    except KeyError as exc:
        supported = ", ".join(REQUIRED_SECOND_ZIP_DATASETS)
        raise SecondZipArchiveValidationError(
            f"Unsupported 2nd.zip dataset '{dataset_name}'. Expected one of: {supported}."
        ) from exc
