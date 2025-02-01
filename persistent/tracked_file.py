import json
import os.path
import time
from dataclasses import dataclass, asdict
import hashlib
import shutil
from pathlib import Path
from typing import Optional

# Constants:
__FOUR_KILOBYTES: int = 4096
__PROJECT_DIRECTORY: str = "\\Users\\tomja\\source\\repos\\retrace\\retrace"
__BACKUP_DIRECTORY: str = __PROJECT_DIRECTORY + "\\.tracking"


@dataclass
class TrackedFile:
	# Instance fields:
	filename: str
	path: str
	hash: str
	size: int
	last_modified: str
	backup_path: str

	# Instance methods:
	def to_json(self):
		return json.dumps(asdict(self), indent=4)

	# Class methods:
	@staticmethod
	def from_json(json_data):
		return TrackedFile(**json.loads(json_data))


# Functions:
def calculate_file_hash(filepath: str) -> str:
	hasher = hashlib.sha256()

	try:
		# Open the file in read-binary mode.
		with open(filepath, "rb") as file:
			# Foreach 4KB chunk in the binary file... (:= is the walrus operator).
			while chunk := file.read(__FOUR_KILOBYTES):
				hasher.update(chunk)

		return hasher.hexdigest()

	except Exception as exception:
		print(f"Error calculating file hash: {exception}")


def backup_file(tracked_file: TrackedFile) -> bool:
	try:
		if os.path.exists(tracked_file.path):
			# Ensure the backup directory exists.
			os.makedirs(os.path.dirname(tracked_file.backup_path), exist_ok=True)

			# Produce a copy of the file (including the metadata) using the shell utilities module.
			shutil.copy2(tracked_file.path, tracked_file.backup_path)

			return True

	except Exception as exception:
		print(f"Error backing up file: {exception}")
		return False


def restore_file(tracked_file: TrackedFile) -> bool:
	if not os.path.exists(tracked_file.backup_path):
		return False

	shutil.copy2(tracked_file.backup_path, tracked_file.path)
	return True


def try_create_tracked_file(filepath: Path, backup_directory: Path) -> Optional[TrackedFile]:
	# Validate the filepath. If the path is invalid, then return none.
	if not filepath.exists() or not filepath.is_file():
		return None

	# Otherwise, initialise a tracked file instance.
	result: TrackedFile = TrackedFile(
		path=filepath.absolute().as_posix(),
		hash=calculate_file_hash(filepath),
		size=filepath.stat().st_size,
		last_modified=time.ctime(filepath.stat().st_mtime),
		backup_path=backup_directory.absolute().as_posix(),
		filename=filepath.name
	)

	return result
