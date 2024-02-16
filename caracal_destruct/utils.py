import os

class File(str):
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise FileNotFoundError(f"File '{filename}' does not exist.")
        self.filename = filename
        self.abspath = os.path.abspath(filename)
        self.isdir = os.path.isdir(filename)
        self.isfile = os.path.isfile(filename)
        self.basename = os.path.basename(filename)