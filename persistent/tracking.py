import json
import os.path
import time
from dataclasses import dataclass, asdict
import hashlib
import shutil
from pathlib import Path, PurePath
from typing import Tuple, Optional

import tracked_file
from tracked_file import TrackedFile, try_create_tracked_file, __PROJECT_DIRECTORY, __BACKUP_DIRECTORY, calculate_file_hash

# Constants:
METADATA_PATH_EXTENSION: str = ".tracking"
TRACKING_FILENAME: str = "tracking_files.json"

"""

	Example JSON data-structure layout.
	
	{
		files: []
	}


"""


@dataclass
class TrackingDAO:
	# Instance fields:
	files: list[TrackedFile]
	directory: Path
	tracking_directory: Path
	tracking_file: Path

	# Methods:
	def backup(self) -> bool:
		if not self.tracking_file.exists() or not self.tracking_file.is_file() or not self.tracking_directory.exists():
			return False

		for file in self.files:
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
		if not self.tracking_directory.exists() or self.tracking_directory.is_file():
			return False

		for file in self.files:
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

		self.files.append(tracked_file)

	def save(self):
		try:
			with open(self.tracking_file.absolute().as_posix(), "w") as file:
				json.dump([asdict(i) for i in self.files], file, indent=4)
			return True

		except Exception as exception:
			return False

	def check(self) -> list[TrackedFile]:
		results: list[TrackedFile] = []

		for file in self.files:
			location: Path = Path(file.path)
			# If the path to the file is invalid, then continue as the file cannot be checked.
			if not location.exists() or location.is_dir():
				continue

			if file.hash != calculate_file_hash(location.absolute().as_posix()):
				results.append(file)

			return results

		return results

	def load(self):
		try:
			with open(self.tracking_file.absolute().as_posix(), "r") as file:
				data = json.load(file)  # Load JSON data as a list of dictionaries.
			self.files = [TrackedFile(**entry) for entry in data]

		except Exception as exception:
			return


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
		files=[],
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
			files=[],
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

