import json
import os.path
import time
from dataclasses import dataclass, asdict
import shutil
from pathlib import Path, PurePath
from typing import Tuple, Optional
import tracked_file
from tracked_file import TrackedFile, try_create_tracked_file, __PROJECT_DIRECTORY, __BACKUP_DIRECTORY, calculate_file_hash
import exceptions

# Constants:
METADATA_PATH_EXTENSION: str = ".tracking"
TRACKING_FILENAME: str = "tracking_files.json"


@dataclass
class TrackingDAO:
	# Instance fields:
	files: dict[str, TrackedFile]
	directory: Path
	tracking_directory: Path
	tracking_file: Path

	# Methods:
	def is_valid(self) -> bool:
		"""
		A tracking DAO is considered valid when the appropriate tracking directories and files are valid and present.

		:return: True when the metadata (.tracking) directory and file (tracking_files.json) exist, False if either resource do not exist.
		"""

		return self.directory.exists() and self.directory.is_dir() and self.tracking_file.exists() and self.tracking_file.is_file()

	def backup(self) -> bool:
		if not self.is_valid():
			return False

		for file in self.files.values():
			location: Path = Path(file.path)
			backup_location: Path = Path(file.backup_path)

			if not location.exists() or location.is_dir() or not backup_location.exists() or backup_location.is_file():
				continue

			# Produce a copy of the file (including the metadata) using the shell utilities' module.
			shutil.copy2(file.path, file.backup_path)
			file.hash = calculate_file_hash(file.path)
			file.last_modified = time.ctime(location.stat().st_mtime)

		self.save()
		return True

	def restore(self) -> bool:
		if not self.is_valid():
			return False

		for file in self.files.values():
			tracked_file.restore_file(file)

		return True

	def add_tracking(self, filename: str) -> bool:
		filepath: Path = self.directory.joinpath(filename)

		# If the file does not exist, or the file is actually a directory, then return false.
		if not filepath.exists() or filepath.is_dir():
			return False

		# Otherwise, add the file to the list of tracked files.
		tracked_file: TrackedFile = try_create_tracked_file(filepath, self.tracking_directory)
		if tracked_file is None:
			return False

		self.files[filename] = tracked_file

	def save(self):
		try:
			with open(self.tracking_file.absolute().as_posix(), "w") as file:
				json.dump({key: asdict(value) for key, value in self.files.items()}, file, indent=4)
			return True

		except Exception as exception:
			return False

	def check(self) -> list[TrackedFile]:
		results: list[TrackedFile] = []

		for file in self.files.values():
			location: Path = Path(file.path)
			# If the path to the file is invalid, then continue as the file cannot be checked.
			if not location.exists() or location.is_dir():
				continue

			if file.hash != calculate_file_hash(location.absolute().as_posix()):
				results.append(file)

			return results

		return results

	def load(self) -> None:
		try:
			with open(self.tracking_file.absolute().as_posix(), "r") as file:
				data = json.load(file)
			self.files = {key: TrackedFile(**value) for key, value in data.items()}

		except Exception as exception:
			return

	def matches_backup(self, filename: str) -> bool:
		if not self.files.__contains__(filename):
			raise exceptions.TrackingDAOException(f"Error: the file: {filename}, is not tracked.", exceptions.TrackingDAOErrorCode.INVALID_TRACKING_FILE)
		return self.files[filename].hash == calculate_file_hash(self.files[filename].path)


def get_tracking_directory(directory: Path) -> Optional[TrackingDAO]:
	if not directory.exists() or directory.is_file():
		return None

	tracking_directory: Path = directory.joinpath(METADATA_PATH_EXTENSION)
	tracking_file_directory: Path = tracking_directory.joinpath(TRACKING_FILENAME)

	# If the folder does not yet have tracking, initialise the tracking directory.
	if not tracking_directory.exists():
		os.mkdir(tracking_directory.absolute().as_posix())

	if not tracking_file_directory.exists():
		os.mkdir(tracking_file_directory)

	return TrackingDAO(
		files={},
		directory=directory,
		tracking_directory=tracking_directory,
		tracking_file=tracking_file_directory
	)


def initialise_tracking(directory: Path) -> Optional[TrackingDAO]:
	try:
		# If the path is invalid or trailing to a file, then exit the function as no directory can be tracked.
		if not directory.exists() or directory.is_file():
			return None

		# Otherwise, create a hidden '.tracking' folder to contain metadata about directory being tracked.
		metadata_directory: Path = directory.joinpath(METADATA_PATH_EXTENSION)
		if not metadata_directory.exists():
			os.mkdir(metadata_directory.absolute().as_posix())

		# Finally, create a tracking file (or override the previous version of the tracking file).
		metadata_file: Path = metadata_directory.joinpath(TRACKING_FILENAME)
		with open(metadata_file.absolute().as_posix(), "w") as file:
			json.dump({}, file)

		if not metadata_directory.exists() or not metadata_file.exists() or metadata_file.is_dir():
			return None

		return TrackingDAO(
			files={},
			directory=directory,
			tracking_directory=metadata_directory,
			tracking_file=metadata_file
		)

	except Exception as exception:
		return None


def insert(file: TrackedFile, tracking_directory_path: Path) -> bool:
	if file is None:
		return False

	tracking_file = tracking_directory_path.joinpath(TRACKING_FILENAME)
	if not tracking_file.exists() or not tracking_file.is_file():
		return False

	with open(tracking_file.absolute().as_posix(), "w") as write:
		write.write(file.to_json())
