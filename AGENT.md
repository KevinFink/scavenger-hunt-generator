# Scavenger Hunt Generator

## Build/Test/Run Commands
- Install dependencies: `poetry install`
- Run the generator: `poetry run python scavenger_hunt_generator.py --num_groups N [--spreadsheet_name NAME | --spreadsheet_id ID] [--share emails]`
- Test command: `poetry run python scavenger_hunt_generator.py --num_groups 2 --spreadsheet_name "Test Hunt" --seed 42`
- Lint: `poetry run ruff check .`
- Format: `poetry run ruff format .`
- Install pre-commit hooks: `poetry run pre-commit install`
- Pre-commit hooks automatically run ruff check and format

## Architecture
- Single Python module with Google Sheets API integration
- Main classes: `GoogleSheetsHandler` (API wrapper), `ScavengerHuntGenerator` (hunt logic)
- Data models: `Clue` (question/answer), `ClueSequence` (generated hunt sequence)
- External dependencies: Google Sheets API, Google Drive API for sharing
- Input: Google Sheets with "Clues" sheet (columns: question, answer/location/person)
- Output: Master sheet + individual group sheets with constraint-based clue sequences
- Constraints: No shared first clues, no shared consecutive clue pairs between groups, last clue from sheet is final clue for all groups

## Code Style
- Python 3.x with type hints (typing module)
- Dataclasses for data models
- Snake_case for variables/functions, PascalCase for classes
- Docstrings for classes and methods
- Exception handling with try/except blocks
- Use f-strings for string formatting
- Imports: standard library first, then third-party
- Path handling with pathlib.Path
- Command-line args with argparse
