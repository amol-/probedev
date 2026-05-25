"""
File-based storage abstraction.

Shows the collaboration: PhoneBook uses Storage interface.
"""

from typing import List
from models import Person


class FileStorage:
    """
    Persists contacts.
    
    PhoneBook depends on this - key collaboration point.
    """
    
    def __init__(self, filepath: str):
        """Initialize with file path."""
        self.filepath = filepath
    
    def load(self) -> List[Person]:
        """Load contacts from file."""
        # TODO(EVO-060): Implement storage file reading and writing.
        #                Why: Storage needs to persist and load contacts.
        #                Done: load() reads JSON file and deserializes to List[Person].
        #                save() serializes List[Person] to JSON and writes to file.
        #                Non-Goals: Do not add error recovery, validation, or atomic writes.
        return []
    
    def save(self, people: List[Person]) -> None:
        """Save contacts to file."""
        pass
