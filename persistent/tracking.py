import json
import os.path
import time
from dataclasses import dataclass, asdict
import shutil
from pathlib import Path
from typing import Optional
from persistent import tracked_file
from persistent.tracked_file import TrackedFile, try_create_tracked_file, calculate_file_hash
from retrace import exceptions

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

	def backup(self, filename: str) -> bool:
		if not self.is_valid():
			raise exceptions.TrackingDAOException(f"Backup for the file: {filename} could not be complete as the tracking directory is invalid", exceptions.TrackingDAOErrorCode.INVALID_TRACKING_DIRECTORY)

		if not self.files.__contains__(filename):
			raise exceptions.TrackingDAOException(f"Backup could not be complete for the file: {filename} could not be complete as it is not tracked.", exceptions.TrackingDAOErrorCode.INVALID_TRACKING_DIRECTORY)

		location: Path = Path(self.files[filename].path)
		backup_location: Path = Path(self.files[filename].backup_path)

		if not location.exists() or location.is_dir() or not backup_location.exists() or backup_location.is_file():
			raise exceptions.TrackingDAOException(f"Backup could not be complete for the file: {filename} could not be complete as it is not tracked.", exceptions.TrackingDAOErrorCode.INVALID_TRACKING_FILE)

		# Produce a copy of the file (including the metadata) using the shell utilities' module.
		shutil.copy2(location.absolute().as_posix(), backup_location.absolute().as_posix())
		self.files[filename].hash = calculate_file_hash(location.absolute().as_posix())
		self.files[filename].last_modified = time.ctime(location.stat().st_mtime)

		"""
		Backup all:
		
		for file in self.files.values():
			location: Path = Path(file.path)
			backup_location: Path = Path(file.backup_path)

			if not location.exists() or location.is_dir() or not backup_location.exists() or backup_location.is_file():
				continue

			# Produce a copy of the file (including the metadata) using the shell utilities' module.
			shutil.copy2(file.path, file.backup_path)
			file.hash = calculate_file_hash(file.path)
			file.last_modified = time.ctime(location.stat().st_mtime)
		"""

		self.save()
		return True

	def restore(self, *filenames: str) -> list[TrackedFile]:
		if not self.is_valid():
			raise exceptions.TrackingDAOException("Invalid tracking directory.", exceptions.TrackingDAOErrorCode.INVALID_TRACKING_DIRECTORY)

		# Initialise a list of tracked files to maintain a record of the files that are successfully restored.
		restored_files: list[TrackedFile] = []

		for filename in filenames:
			# If a specified file is not tracked, raise an untracked file exception. We could simply ignore restore the file, however, it's best to be explicit
			# about why the file could not be restored, so the issue can be more easily resolved.
			if not self.files.__contains__(filename):
				raise exceptions.TrackingDAOException(f"Attempted to restore an untracked file ({filename}).", exceptions.TrackingDAOErrorCode.UNTRACKED_FILE)

			# If the tracked file is successfully restored, add it to the list of tracked files.
			if tracked_file.restore_file(self.files[filename]):
				restored_files.append(self.files[filename])

		return restored_files

	def track(self, filename: str) -> TrackedFile:
		"""
		Adds tracking to an existing file, adding the file to the list of tracked files upon success.

		This method attempts to add a file, specified by `filename`, to the list of tracked files. It first
		verifies that the file exists and is not a directory. If these conditions are met, the file is
		processed and tracked. If any validation fails or the tracking process encounters an error, an exception
		is raised.

		:param filename: The name of the file to be tracked.
		:type filename: str.

		:return: Returns a `TrackedFile` object that represents the tracked file.
		:rtype: TrackedFile.

		:raises TrackingDAOException: If the file does not exist, is a directory, or if there was a failure in
		creating a tracked file.
		:raises TrackingDAOErrorCode.INVALID_TRACKING_FILE: Error code raised if the file is not valid for tracking.
		"""

		# If the file is already tracked, simply return a reference to the tracked file instance.
		if self.files.__contains__(filename):
			return self.files[filename]

		# Build a reference to the full path leading to the parametrised file.
		filepath: Path = self.directory.joinpath(filename)

		# If the file does not exist, or the file is actually a directory, then return false.
		if not filepath.exists() or filepath.is_dir():
			raise exceptions.TrackingDAOException(f"The file {filename} does not exist as a valid file for the location: {filepath.absolute().as_posix()}.", exceptions.TrackingDAOErrorCode.INVALID_TRACKING_FILE)

		# Otherwise, add the file to the list of tracked files.
		file: TrackedFile = try_create_tracked_file(filepath, self.tracking_directory)
		if tracked_file is None:
			raise exceptions.TrackingDAOException(f"Failed to track the file: {filename}.", exceptions.TrackingDAOErrorCode.INVALID_TRACKING_FILE)

		self.files[filename] = tracked_file
		return tracked_file

	def save(self):
		try:
			with open(self.tracking_file.absolute().as_posix(), "w") as file:
				json.dump({key: asdict(value) for key, value in self.files.items()}, file, indent=4)
			return True

		except Exception as exception:
			return False

	def load(self) -> None:
		try:
			with open(self.tracking_file.absolute().as_posix(), "r") as file:
				data = json.load(file)
			self.files = {key: TrackedFile(**value) for key, value in data.items()}

		except Exception as exception:
			return

	def matches_backup(self, filename: str) -> bool:
		"""
		Verifies if the file specified by the given filename matches the identity of its backup. If the file
		does not match the identity of its backup file, this means the file has changed since the previous backup.

		This method checks whether the file exists in the list of tracked files and if its hash matches the
		hash of the backup file stored in the tracking data. If the file is not tracked or the hash does
		not match, an exception is raised.

		:param filename: The name of the file to check for matching hash. It must be a tracked file.
		:type filename: str.

		:return: Returns True if the file's hash matches the stored hash for its backup.
		:rtype: bool.

		:raises TrackingDAOException: If the file is not found in the list of tracked files or if the hashes do not match.
		:raises TrackingDAOErrorCode.INVALID_TRACKING_FILE: If the file specified by `filename` is not tracked.
		"""

		if not self.files.__contains__(filename):
			raise exceptions.TrackingDAOException(f"The file: {filename}, is not tracked.", exceptions.TrackingDAOErrorCode.INVALID_TRACKING_FILE)
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
