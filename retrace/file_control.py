import os


print("Hello, World!")

# Constants:
PROJECT_DIRECTORY: str = "\\Users\\tomja\\source\\repos\\retrace\\retrace"
HIDDEN_DIR_NAME: str = "../.tracking"

# Functions:
def create_repository(directory_path: str):
    try:
        if not os.path.isdir(directory_path):
            print(f"Error: the path: '{directory_path}' does not exist.")
            return

        # Note to self - Add logic for hidden path on windows.
        os.mkdir(directory_path+"\\"+HIDDEN_DIR_NAME)
        print(f"Successfully initialised file tracking for the directory: '{directory_path}'.")

    except FileExistsError:
        print(f"Error, directory already has tracking.")

    except PermissionError:
        print(f"Permission denied: unable to initialise file tracking.")

    except Exception as exception:
        print(f"An error occurred: {exception}")



create_repository(PROJECT_DIRECTORY)


