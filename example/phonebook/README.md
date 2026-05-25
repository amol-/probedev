# Phonebook CLI - Architectural Probe

A **minimal executable skeleton** that surfaces how entities collaborate.
The probe defines the architecture with real imports and method calls, but
defers all actual behavior to TODO(EVO-...) markers.

## Architectural Question

**Do the boundaries CLI → PhoneBook → Storage provide the right collaboration for a phonebook?**

This probe answers by showing the actual collaboration chain in code:
- `phonebook.py` imports `PhoneBook` from `models` and `FileStorage` from `storage`
- `PhoneBook` receives `FileStorage` in its constructor
- CLI commands delegate to `PhoneBook` methods
- `PhoneBook` methods delegate to `Storage` methods

## Current State

The probe is **executable but incomplete**. It runs and shows the collaboration,
but all features print "NOT IMPLEMENTED" or are stubs.

```bash
$ python3 phonebook.py list
display_grouped: NOT IMPLEMENTED

$ python3 phonebook.py add "Alice" "+1234567890"
# (no output - calls PhoneBook.add() which is a stub)
```

## Files & Collaboration

| File | Imports | Collaborates With | EVO Markers |
|------|---------|-------------------|--------------|
| `phonebook.py` | PhoneBook, FileStorage | Calls PhoneBook methods | EVO-070, EVO-080 |
| `models.py` | - | PhoneBook uses Storage | EVO-010, EVO-020, EVO-030, EVO-040, EVO-050 |
| `storage.py` | Person | Used by PhoneBook | EVO-060 |

**Collaboration Chain:** CLI → PhoneBook → Storage

## Evolution Plan

All features are TODO(EVO-...) markers in the files where implementation belongs:

| ID | Feature | File | Location |
|----|---------|------|----------|
| EVO-010 | Define Person class | models.py | Person class |
| EVO-020 | PhoneBook.list() | models.py | list() method |
| EVO-030 | PhoneBook.add() with duplicate check | models.py | add() method |
| EVO-040 | PhoneBook.delete() idempotent | models.py | delete() method |
| EVO-050 | PhoneBook.edit() | models.py | edit() method |
| EVO-060 | FileStorage load/save | storage.py | load()/save() methods |
| EVO-070 | Country code table + extraction | phonebook.py | COUNTRY_CODES + extract_country_code() |
| EVO-080 | Grouped display | phonebook.py | display_grouped() |

Each marker includes Why, Done, and Non-Goals.

## Intent Ledger

Every requirement maps to an evolution:

| Requirement | Evolution |
|-------------|-----------|
| Each person has Name and Number | EVO-010 |
| Number prefixed with international prefix | EVO-030 (validation) |
| Groups by country code with lookup | EVO-070, EVO-080 |
| CLI list command | EVO-020, EVO-080 |
| CLI add command | EVO-030 |
| CLI delete command | EVO-040 |
| CLI edit command | EVO-050 |
| Delete is idempotent | EVO-040 |
| Unique key is phone number | EVO-030, EVO-040, EVO-050 |
| Add errors on duplicate | EVO-030 |
| File storage | EVO-060 |

## No Duplicate Markers

All TODO(EVO-...) markers are unique and in the file where work belongs:

```bash
$ grep -h "TODO(EVO-" *.py | sed 's/.*TODO(EVO-\([0-9]*\).*/\1/' | sort | uniq -d
# (produces no output - no duplicates)
```

## What This Probe Proves

1. ✅ **Boundaries are clear**: CLI, Models, Storage are separate
2. ✅ **Integration points work**: Real imports, real method calls
3. ✅ **Collaboration is visible**: CLI → PhoneBook → Storage chain
4. ✅ **Easy to remove**: Just delete the directory
5. ✅ **Easy to evolve**: Each EVO is where implementation belongs
6. ✅ **No duplicate markers**: Each EVO is unique

## Success Criteria

✅ Boundaries make sense (CLI/Models/Storage)  
✅ Names are clear (Person, PhoneBook, FileStorage)  
✅ Integration points are correct (real imports, real calls)  
✅ Flow is understandable (CLI → PhoneBook → Storage)  
✅ Easy to remove  
✅ Evolution plan covers all features  
✅ Can predict implementation from markers  
✅ **Entities actually collaborate**  
