import cmd
from pathlib import Path
from typing import Optional

from persistent import tracking


class CLI(cmd.Cmd):
	# Class fields:
	prompt = "ft> "

	# Constructor:
	def __init__(self):
		super().__init__()
		# Instance fields:
		self.__tracking_dao: Optional[tracking.TrackingDao] = None

	# Instance methods:
	def do_hello(self, arg):
		print(f"Hello, {arg}!")

	def do_load(self, arg: str):
		self.__tracking_dao = tracking.get_tracking_directory(Path(arg))

		# If the function failed to load a valid tracking DAO, then exit the method.
		if self.__tracking_dao is None:
			print(f"Failed to load the tracking for the directory at: {arg}")
			return

		# Otherwise, load the tracking resources onto the tracking DAO instance.
		self.__tracking_dao.load()
		print(f"Successfully loaded the tracking directory at location: {arg}")

	def do_files(self, arg):
		if self.__tracking_dao is None:
			print(f"Error, the no tracking directory is loaded.")
			return

		# Output each file that is tracked.
		print(f"Tracking files:")
		for file in self.__tracking_dao.files:
			print(f"* {file}")

	def do_init(self, arg):
		dao: Optional[tracking.TrackingDAO] = tracking.initialise_tracking(Path(arg))

		# If the function returns nothing, then the initialisation failed and no tracking directory has been created.
		if dao is None:
			print(f"Error, failed to initialise directory at location: {Path(arg)}")
			return

		self.__tracking_dao = dao
		print(f"Successfully initialised directory at location: {Path(arg)}")

	def do_add(self, arg):
		if self.__tracking_dao is None:
			print(f"Error, no tracking directory is loaded.")
			return

		if self.__tracking_dao.add_tracking(arg) is False:
			print(f"Error, {arg} is an invalid file.")
			return

		self.__tracking_dao.save()
		print(f"Successfully added the file {arg} to tracking.")

	def do_check(self, arg):
		if self.__tracking_dao is None:
			print(f"Error, no tracking directory is loaded")
			return

		files: list[tracking.TrackedFile] = self.__tracking_dao.check()
		print(f"The following files that have changed since their last backup:")
		for file in files:
			print(f"* {file}")

	def do_backup(self, arg):
		if self.__tracking_dao is None:
			print(f"Error, no tracking directory is loaded")
			return

		self.__tracking_dao.backup()

	def do_restore(self, arg):
		if self.__tracking_dao is None:
			print(f"Error, no tracking directory is loaded")
			return

		if self.__tracking_dao.restore():
			print(f"Successfully restored files.")
			return

		print("fError, could not restore the files.")


if __name__ == "__main__":
	CLI().cmdloop()
