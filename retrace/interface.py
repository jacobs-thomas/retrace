import cmd
from pathlib import Path
from typing import Optional
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
	def do_load(self, arg: str):
		"""
		Hello

		:param arg:
		:return:
		"""

		self._tracking_dao = tracking.get_tracking_directory(Path(arg))

		# If the function failed to load a valid tracking DAO, then exit the method.
		if self._tracking_dao is None:
			print(f"Failed to load the tracking for the directory at: {arg}")
			return

		# Otherwise, load the tracking resources onto the tracking DAO instance.
		self._tracking_dao.load()
		print(f"Successfully loaded the tracking directory at location: {arg}")

	@validate_tracking
	def do_files(self, arg):
		# Output each file that is tracked.
		print(f"Tracking files:")
		for file in self._tracking_dao.files.values():
			print(f"* {file.filename}")

	def do_init(self, arg):
		dao: Optional[tracking.TrackingDAO] = tracking.initialise_tracking(Path(arg))

		# If the function returns nothing, then the initialisation failed and no tracking directory has been created.
		if dao is None:
			print(f"Error, failed to initialise directory at location: {Path(arg)}")
			return

		self._tracking_dao = dao
		print(f"Successfully initialised directory at location: {Path(arg)}")

	@validate_tracking
	def do_add(self, arg):
		if self._tracking_dao.add_tracking(arg) is False:
			print(f"Error, {arg} is an invalid file.")
			return

		self._tracking_dao.save()
		print(f"Successfully added the file {arg} to tracking.")

	@validate_tracking
	def do_check(self, arg):
		files: list[tracking.TrackedFile] = self._tracking_dao.check()
		print(f"The following files that have changed since their last backup:")
		for file in files:
			print(f"* {file}")

	@validate_tracking
	def do_check_file(self, arg):
		# Split arguments safely and check if we have a file argument.
		args = arg.split()

		if not args:
			self.do_check_with_no_args(arg)  # Handle case where no file argument is provided.
			return self.do_check(arg)

		try:
			# Assume matches_backup returns a boolean indicating if the file is up-to-date.
			result = self._tracking_dao.matches_backup(args[0])

			# Provide more readable output depending on the result.
			if result:
				print(f"The file: {args[0]} has not changed since its last backup.")
			else:
				print(f"The file: {args[0]} has changed since its last backup.")

		except exceptions.TrackingDAOException as exception:
			# Handle exceptions more gracefully with a clear message.
			print(f"Error checking file '{args[0]}': {exception}")

	@validate_tracking
	def do_backup(self, arg):
		self._tracking_dao.backup()

	@validate_tracking
	def do_restore(self, arg):
		if self._tracking_dao.restore():
			print(f"Successfully restored files.")
			return

		print("fError, could not restore the files.")
