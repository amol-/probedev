"""
Phonebook domain models.

Shows the collaboration: PhoneBook uses Storage, CLI uses PhoneBook.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Person:
    """
    Represents a contact with name and phone number.
    
    TODO(EVO-010): Define Person with name and number fields.
    Why: Need a data structure to hold contact information.
    Done: Person is a dataclass with name (str) and number (str) fields.
    Non-Goals: Do not add additional fields like email or address.
    """
    name: str
    number: str


class PhoneBook:
    """
    Manages contacts and delegates persistence to Storage.
    
    Shows collaboration: receives Storage in constructor, uses it for load/save.
    """
    
    def __init__(self, storage):
        """PhoneBook depends on Storage - key collaboration point."""
        self._storage = storage
    
    def list(self) -> List[Person]:
        """List all contacts.
        
        TODO(EVO-020): Return contacts for display.
        Why: list command needs access to all contacts.
        Done: Returns a list of Person objects loaded from Storage.
        Non-Goals: Do not implment grouping or sorting.
        """
        return []
    
    def add(self, name: str, number: str) -> None:
        """
        Add a new contact.
        
        TODO(EVO-030): Implement with duplicate checking.
        Why: Phone numbers must be unique.
        Done: Checks if number exists in self._people, creates Person,
        adds to list, calls save().
        Non-Goals: Do not add validation beyond duplicate check.
        """
        pass
    
    def delete(self, number: str) -> bool:
        """
        Delete a contact by phone number.
        
        TODO(EVO-040): Implement with idempotent behavior.
        Why: Delete should be safe to call multiple times.
        Done: Finds Person by number, removes from list, calls save().
        Returns True if found and deleted, False otherwise.
        Non-Goals: Do not add confirmation or cascade delete.
        """
        pass
    
    def edit(self, number: str, new_name: Optional[str] = None, new_number: Optional[str] = None) -> None:
        """
        Edit a contact by phone number.
        
        TODO(EVO-050): Implement update logic.
        Why: Users need to update existing contacts.
        Done: Finds Person by number, updates name/number (validating
        new_number isn't a duplicate), calls save().
        Non-Goals: Do not add partial updates or history tracking.
        """
        pass
