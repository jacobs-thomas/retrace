import cmd
from pathlib import Path
from typing import Optional

import retrace.exceptions
from retrace import exceptions
from persistent import tracking
import functools
from typing import Callable, TypeVar

# Decorator:
T = TypeVar("T", bound=Callable)


def validate_tracking(function: T) -> T:
	"""Decorator to ensure a valid tracking directory is loaded before running a command."""

	@functools.wraps(function)  # Preserve function metadata
	def wrapper(self, *args, **kwargs):
		# Ensure self is an instance of CLI (runtime check)
		if not isinstance(self, RetraceCLI):
			raise TypeError(f"Expected 'self' to be instance of CLI, got {type(self).__name__}")

		# Validate tracking DAO
		if self._tracking_dao is None or not self._tracking_dao.is_valid():
			print(f"Error: No valid tracking directory is loaded.")
			return

		return function(self, *args, **kwargs)

	return wrapper


class RetraceCLI(cmd.Cmd):
	"""
	An entry point into the retrace command line interface.
	"""

	# Class fields:
	prompt = "ft> "

	# Constructor:
	def __init__(self):
		super().__init__()
		# Instance fields:
		self._tracking_dao: Optional[tracking.TrackingDao] = None

	# Instance methods:
	def do_load(self, directory_path: str) -> None:
		"""
		Loads the tracking directory and initializes tracking resources.

		This method sets the tracking DAO instance to the specified tracking directory path and loads
		the associated tracking resources. If the tracking directory is valid, the resources are
		successfully loaded; otherwise, an exception may be raised.

		:param directory_path: The path to the tracking directory.
		:type directory_path: str.

		:return: None.
		:rtype: None.

		:raises TrackingDAOException: If there is an issue loading the tracking directory.
		"""

		self._tracking_dao = tracking.get_tracking_directory(Path(directory_path))
		if self._tracking_dao is None:
			print(f"Error, the path: '{directory_path}' led to an invalid tracking directory.")
			return

		# Load the tracking resources onto the tracking DAO instance.
		self._tracking_dao.load()
		print(f"Successfully loaded the tracking directory at location: {directory_path}")

	@validate_tracking
	def do_files(self, argument: str) -> None:
		"""
		Displays a list of tracked files.

		This method retrieves and prints all tracked files from the tracking DAO instance. Each tracked
		file's filename is displayed in the output.

		:param argument: Unused parameter (included for compatibility with command handling).
		:type argument: str.

		:return: None.
		:rtype: None.
		"""

		# Output each file that is tracked.
		print(f"Tracking files:")
		for file in self._tracking_dao.files.values():
			print(f"* {file.filename}")

	def do_init(self, arg):
		dao: Optional[tracking.TrackingDAO] = tracking.initialise_tracking(Path(arg))

		# If the function returns nothing, then the initialisation failed and no tracking directory has been created.
		if dao is None:
			print(f"Error, failed to initialise directory at location: {Path(arg)}.")
			return

		self._tracking_dao = dao
		print(f"Successfully initialised directory at location: {Path(arg)}.")

	@validate_tracking
	def do_track(self, argument: str) -> None:
		"""
		Adds a file to the tracking system.

		This method attempts to track the specified file by adding it to the tracking DAO. If successful,
		the tracking state is saved, and a confirmation message is printed. If tracking fails due to an
		exception, an error message is displayed instead.

		:param argument: The name or path of the file to be tracked.
		:type argument: str.

		:return: None.
		:rtype: None.

		:raises TrackingDAOException: If an error occurs while attempting to track the file.
		"""

		try:
			file = self._tracking_dao.track(argument)
			self._tracking_dao.save()
			print(f"Successfully added tracking for the file: {argument}.")

		except retrace.exceptions.TrackingDAOException as exception:
			print(f"Error tracking file: {exception}.")

	@validate_tracking
	def do_check(self, argument: str) -> None:
		"""
		Checks for changes in tracked files since the last backup.

		This method retrieves a list of tracked files that have been modified since their last recorded
		backup and displays them in the output.

		:param argument: Unused parameter (included for compatibility with command handling).
		:type argument: str.

		:return: None.
		:rtype: None.
		"""

		# Retrieve the list of tracked files that have changed since the last backup.
		files: list[tracking.TrackedFile] = self._tracking_dao.check()

		print("The following files have changed since their last backup:")
		for file in files:
			print(f"* {file}")

	@validate_tracking
	def do_check_file(self, argument: str) -> None:
		"""
		Checks whether a specific tracked file has changed since its last backup.

		This method determines if the specified file has been modified since the last backup. If no
		filename is provided, it delegates to `do_check_with_no_args` and `do_check` to handle the request.
		If a filename is given, it checks whether the file has changed and prints an appropriate message.
		Any errors encountered during the check are gracefully handled.

		:param argument: The filename to check for modifications.
		:type argument: str.

		:return: None.
		:rtype: None.

		:raises TrackingDAOException: If an error occurs while checking the file's status.
		"""

		# Split arguments safely and check if we have a file argument.
		arguments = argument.split()

		if not arguments:
			return self.do_check(argument)

		try:
			# Provide more readable output depending on the result.
			if self._tracking_dao.matches_backup(arguments[0]):
				print(f"The file: {arguments[0]} has not changed since its last backup.")
				return

			print(f"The file: {arguments[0]} has changed since its last backup.")

		except exceptions.TrackingDAOException as exception:
			# Handle exceptions more gracefully with a clear message.
			print(f"Error checking file '{arguments[0]}': {exception}")

	@validate_tracking
	def do_backup(self, argument: str) -> None:
		"""
		Creates a backup for the specified tracked file(s).

		This method attempts to back up one or more tracked files. If no filename is provided,
		an error message is displayed. Otherwise, the specified files are backed up, and a
		success message is printed for each file. If an error occurs during the backup process,
		it is handled gracefully, and an error message is displayed.

		:param argument: The filename(s) to back up, separated by spaces.
		:type argument: str.

		:return: None.
		:rtype: None.

		:raises TrackingDAOException: If an error occurs during the backup process.
		"""

		# Split arguments safely and check if we have a file argument.
		arguments = argument.split()

		if not arguments:
			print("Error: no file was specified for backup.")
			return

		try:
			# Attempt to back up the specified files.
			files: list[tracking.TrackedFile] = self._tracking_dao.backup(*arguments)
			print("Successfully produced a backup for the file(s):")
			for file in files:
				print(f"* {file.filename}.")

		except exceptions.TrackingDAOException as exception:
			# Handle errors gracefully with a clear message.
			print(f"Error, failed to backup file: {exception}.")

	@validate_tracking
	def do_restore(self, argument: str) -> None:
		"""
		Restores the specified tracked file(s) from a backup.

		This method attempts to restore one or more previously backed-up files. If no filename
		is provided, an error message is displayed. Otherwise, the specified files are restored,
		and a success message is printed for each restored file. If an error occurs during
		restoration, it is handled gracefully, and an error message is displayed.

		:param argument: The filename(s) to restore, separated by spaces.
		:type argument: str.

		:return: None.
		:rtype: None.

		:raises TrackingDAOException: If an error occurs during the restoration process.
		"""

		# Split arguments safely and check if we have a file argument.
		arguments = argument.split()

		if not arguments:
			print("Error: no file was specified for backup.")
			return

		try:
			# Restore each of the parameterized files.
			restored_files: list[tracking.TrackedFile] = self._tracking_dao.restore(*arguments)

			# Inform the user of the files that have been successfully restored.
			print("Successfully restored the following files:")
			for tracked_file in restored_files:
				print(f"* {tracked_file.filename}")

		except exceptions.TrackingDAOException as exception:
			# Handle errors gracefully with a clear message and error code.
			print(f"Error, failed to restore file(s). Exception message: {exception} [{exception.error_code}]")
