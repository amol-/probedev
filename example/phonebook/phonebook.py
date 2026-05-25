#!/usr/bin/env python3
"""
Phonebook CLI - Main entrypoint.

Exposes the collaboration between CLI, PhoneBook, and Storage.
All commands delegate to PhoneBook methods, which delegate to Storage.
"""

import argparse
import sys

from models import PhoneBook
from storage import FileStorage


COUNTRY_CODES = {}

def main():
    """CLI entrypoint - delegates all commands to PhoneBook."""
    parser = _build_parser()
    args = parser.parse_args()
    
    # Initialize storage and phonebook - shows the collaboration chain
    # CLI -> PhoneBook -> Storage
    storage = FileStorage("~/.phonebook.json")
    phonebook = PhoneBook(storage)
    
    if args.command == "list":
        display_grouped(phonebook)
    
    elif args.command == "add":
        phonebook.add(args.name, args.number)
    
    elif args.command == "delete":
        phonebook.delete(args.number)
    
    elif args.command == "edit":
        phonebook.edit(args.number, args.new_name, args.new_number)
    
    else:
        parser.print_help()
        sys.exit(1)


def extract_country_code(phone_number: str, country_codes: dict) -> str:
    """Extract country name from phone number using lookup table."""
    # TODO(EVO-070): Add country code to name lookup table and extraction.
    #                Why: Need to map country code prefixes (e.g., +1, +44) to country names
    #                for grouping contacts by country in the list command.
    #                Done: COUNTRY_CODES dictionary exists with all common prefix mappings,
    #                extract_country_code() parses numbers correctly.
    #                Non-Goals: Do not add phone number validation or formatting in this step.
    return "Unknown"


def display_grouped(phonebook: PhoneBook) -> None:
    """
    Display phonebook contacts grouped by country.
    
    TODO(EVO-080): Implement grouped display using COUNTRY_CODES.
    Why: Core feature - list command must show contacts organized by country.
    Done: Contacts are fetched from PhoneBook, grouped by country code,
    and displayed with country name headers.
    Non-Goals: Do not add sorting, filtering, or pagination in this step.
    """
    contacts = phonebook.list()
    # Group by country and display
    print("display_grouped: NOT IMPLEMENTED")


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        description="Simple phonebook with country code grouping"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # List command - delegates to PhoneBook.list()
    subparsers.add_parser("list", help="List all contacts grouped by country")
    
    # Add command - delegates to PhoneBook.add()
    add_parser = subparsers.add_parser("add", help="Add a new contact")
    add_parser.add_argument("name", help="Contact name")
    add_parser.add_argument("number", help="Phone number with international prefix")
    
    # Delete command - delegates to PhoneBook.delete()
    delete_parser = subparsers.add_parser("delete", help="Delete a contact by phone number")
    delete_parser.add_argument("number", help="Phone number to delete")
    
    # Edit command - delegates to PhoneBook.edit()
    edit_parser = subparsers.add_parser("edit", help="Edit a contact by phone number")
    edit_parser.add_argument("number", help="Phone number of contact to edit")
    edit_parser.add_argument("new_name", nargs="?", help="New name (optional)")
    edit_parser.add_argument("new_number", nargs="?", help="New phone number (optional)")
    
    return parser





if __name__ == "__main__":
    main()
