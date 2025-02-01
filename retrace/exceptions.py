from enum import Enum


# Enumerations:
class TrackingDAOErrorCode(Enum):
	INVALID_TRACKING_DIRECTORY = 0,
	INVALID_TRACKING_FILE = 1,


# Exceptions:
class TrackingDAOException(Exception):
	"""
	Exception raised for errors that occur within the TrackingDAO (Data Access Object) operations.

	This custom exception class is designed to provide detailed information about errors
	encountered during interactions with the TrackingDAO. It allows you to store both
	an error message and an associated error code, which can be used for debugging, logging,
	or user feedback. All exceptions related to the TrackingDAO should inherit from this base
	exception class.

	Attributes:
		error_code (TrackingDAOErrorCode): An enumerated error code that categorizes the error.

	Methods:
		__init__(self, message: str, error_code: TrackingDAOErrorCode):
			Initializes the TrackingDAOException with a message and an error code.

	Example:
		raise TrackingDAOException("Database connection failed", TrackingDAOErrorCode.CONNECTION_ERROR)
	"""

	# Initializer:
	def __init__(self, message: str, error_code: TrackingDAOErrorCode):
		"""
		Initialises the exception with the given error message and error code.

		Args:
			message (str): A descriptive message about the error.
			error_code (TrackingDAOErrorCode): The error code that categorizes the error.

		The message is passed to the base `Exception` class to handle standard exception behavior.
		The error code is stored as an instance attribute for reference.
		"""

		self.error_code = error_code
		super().__init__(message)