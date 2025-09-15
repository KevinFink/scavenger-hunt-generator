#!/usr/bin/env python3

import argparse
import random
import sys
from typing import List, Dict, Optional
from dataclasses import dataclass
import os
import pickle
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import time
import socket
from datetime import datetime
import http.client

# Google Sheets API scopes
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@dataclass
class Clue:
    """Represents a clue in the scavenger hunt"""

    question: str
    answer: str
    clue_type: Optional[str] = None


@dataclass
class ClueSequence:
    """Represents a clue sequence for a group"""

    clue_number: int
    question: str
    location: str
    next_clue: str


class GoogleSheetsHandler:
    """Handle Google Sheets integration for scavenger hunt"""

    def __init__(
        self, credentials_path: Optional[str] = None, token_path: Optional[str] = None
    ):
        self.credentials_path = credentials_path or Path("credentials.json")
        self.token_path = token_path or Path("token_rw.pickle")
        self.service = None
        self.drive_service = None

    def establish_google_creds(self):
        """Establish Google credentials for API access"""
        creds = None

        if os.path.exists(self.token_path):
            with open(self.token_path, "rb") as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open(self.token_path, "wb") as token:
                pickle.dump(creds, token)

        return creds

    def get_google_sheets_service(self):
        """Get Google Sheets service instance"""
        if self.service is None:
            credentials = self.establish_google_creds()
            self.service = build(
                "sheets", "v4", credentials=credentials, cache_discovery=False
            )
        return self.service

    def get_google_drive_service(self):
        """Get Google Drive service instance"""
        if self.drive_service is None:
            credentials = self.establish_google_creds()
            self.drive_service = build(
                "drive", "v3", credentials=credentials, cache_discovery=False
            )
        return self.drive_service

    def _gsheet_execute(self, method, quiet: bool = False):
        """Execute a Google Sheets API method with retry logic"""
        success = False
        while not success:
            try:
                response = method.execute()
                success = True
            except HttpError as e:
                if e.resp.status >= 500 or e.resp.status == 429 or e.resp.status == 409:
                    if not quiet:
                        print(
                            f"HttpError {e.resp.status}: {http.client.responses.get(e.resp.status, 'Unknown Error')}"
                        )
                        print(
                            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Sleeping for 30 seconds before retrying..."
                        )
                    time.sleep(30)
                else:
                    raise
            except (TimeoutError, socket.error) as e:
                if not quiet:
                    print(f"Network error: {e}")
                    print(
                        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Sleeping for 30 seconds before retrying..."
                    )
                time.sleep(30)
        return response

    def find_google_sheet(self, sheet_name: str) -> Optional[str]:
        """Find a Google Sheet by name"""
        service = self.get_google_drive_service()

        query = f"name = '{sheet_name}' and mimeType = 'application/vnd.google-apps.spreadsheet'"
        try:
            response = (
                service.files()
                .list(q=query, fields="files(id, name)", pageSize=1)
                .execute()
            )
            files = response.get("files", [])
            if files:
                return files[0]["id"]
            return None
        except Exception as e:
            print(f"Error while searching for spreadsheet: {e}")
            return None

    def sheet_exists(self, spreadsheet_id: str, sheet_name: str) -> bool:
        """Check if a sheet exists in the spreadsheet"""
        service = self.get_google_sheets_service()

        try:
            method = service.spreadsheets().get(spreadsheetId=spreadsheet_id)
            result = self._gsheet_execute(method)
            existing_sheets = [
                sheet["properties"]["title"] for sheet in result.get("sheets", [])
            ]
            return sheet_name in existing_sheets
        except Exception:
            return False

    def read_clues_from_sheet(
        self, spreadsheet_id: str, sheet_name: str = "Clues"
    ) -> List[Clue]:
        """Read clues from a Google Sheet"""
        service = self.get_google_sheets_service()

        range_name = f"{sheet_name}!A:C"
        method = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=spreadsheet_id, range=range_name)
        )
        result = self._gsheet_execute(method)

        values = result.get("values", [])
        if not values:
            raise ValueError("No data found in the sheet")

        clues = []
        # Skip header row if present
        if values[0] and (
            values[0][0].lower() == "clue" or values[0][0].lower() == "question"
        ):
            start_row = 1
        else:
            start_row = 0

        for row in values[start_row:]:
            if len(row) >= 2 and row[0] and row[1]:
                clue_type = row[2].strip() if len(row) >= 3 and row[2] else None
                clues.append(Clue(question=row[0].strip(), answer=row[1].strip(), clue_type=clue_type))

        return clues

    def create_sheet_if_not_exists(self, spreadsheet_id: str, sheet_name: str):
        """Create a new sheet if it doesn't exist"""
        service = self.get_google_sheets_service()

        # Check if sheet exists
        try:
            method = service.spreadsheets().get(spreadsheetId=spreadsheet_id)
            result = self._gsheet_execute(method)
            existing_sheets = [
                sheet["properties"]["title"] for sheet in result.get("sheets", [])
            ]

            if sheet_name not in existing_sheets:
                # Create the sheet
                body = {
                    "requests": [{"addSheet": {"properties": {"title": sheet_name}}}]
                }
                method = service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id, body=body
                )
                self._gsheet_execute(method)
                print(f"Created sheet: {sheet_name}")
        except Exception as e:
            print(f"Error creating sheet {sheet_name}: {e}")

    def create_google_sheet(self, title: str) -> str:
        """Create a new Google Sheet"""
        service = self.get_google_sheets_service()

        spreadsheet = {"properties": {"title": title}}

        method = service.spreadsheets().create(body=spreadsheet, fields="spreadsheetId")
        result = self._gsheet_execute(method)

        return result.get("spreadsheetId")

    def share_google_sheet(
        self, spreadsheet_id: str, emails: List[str], role: str = "writer"
    ) -> bool:
        """Share a Google Sheet with specific email addresses"""
        service = self.get_google_drive_service()

        success = True
        for email in emails:
            try:
                permission = {"type": "user", "role": role, "emailAddress": email}

                method = service.permissions().create(
                    fileId=spreadsheet_id, body=permission, sendNotificationEmail=True
                )

                self._gsheet_execute(method)
                print(f"✅ Shared with {email} ({role} access)")

            except Exception as e:
                print(f"❌ Failed to share with {email}: {e}")
                success = False

        return success

    def write_to_sheet(
        self, spreadsheet_id: str, sheet_name: str, data: List[List[str]]
    ):
        """Write data to a Google Sheet"""
        service = self.get_google_sheets_service()

        # Create sheet if it doesn't exist
        self.create_sheet_if_not_exists(spreadsheet_id, sheet_name)

        # Clear existing data
        range_name = sheet_name
        method = (
            service.spreadsheets()
            .values()
            .clear(spreadsheetId=spreadsheet_id, range=range_name)
        )
        self._gsheet_execute(method)

        # Write new data
        body = {"values": data}
        method = (
            service.spreadsheets()
            .values()
            .update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body,
            )
        )
        self._gsheet_execute(method)
        print(f"Updated sheet: {sheet_name}")


class ScavengerHuntGenerator:
    """Generate scavenger hunt sequences for multiple groups"""

    def __init__(self, clues: List[Clue], num_groups: int):
        self.clues = clues
        self.num_groups = num_groups

    def generate_hunt(self) -> Dict[int, List[ClueSequence]]:
        """Generate scavenger hunt sequences for all groups with constraints"""
        # Use all available clues
        selected_clues = self.clues
        
        if len(selected_clues) < 2:
            raise ValueError("Need at least 2 clues to generate a hunt")

        # Reserve the last clue as the final clue for all groups
        final_clue = selected_clues[-1]
        randomizable_clues = selected_clues[:-1]

        # Create different sequences for each group
        all_sequences = {}
        used_first_clues = set()
        used_consecutive_pairs = set()

        for group_num in range(1, self.num_groups + 1):
            sequence = None
            attempts = 0
            max_attempts = 100  # Prevent infinite loops

            # Keep trying until we find a valid sequence
            while sequence is None and attempts < max_attempts:
                attempts += 1

                # Try to create a sequence that alternates types when possible
                shuffled_clues = self._create_alternating_sequence(randomizable_clues)
                
                # If alternating didn't work well, fall back to random shuffle
                if shuffled_clues is None or self._violates_constraints(shuffled_clues, used_first_clues, used_consecutive_pairs):
                    shuffled_clues = randomizable_clues.copy()
                    random.shuffle(shuffled_clues)
                    
                    # Check if this sequence violates constraints
                    if self._violates_constraints(shuffled_clues, used_first_clues, used_consecutive_pairs):
                        continue  # Try again with a different shuffle

                # Create sequence for this group (randomizable clues + final clue)
                candidate_sequence = []
                
                # Add the randomizable clues
                for i, clue in enumerate(shuffled_clues):
                    clue_number = i + 1

                    # Determine the next clue
                    if i < len(shuffled_clues) - 1:
                        next_clue = shuffled_clues[i + 1].question
                    else:
                        # Next clue is the final clue
                        next_clue = final_clue.question

                    candidate_sequence.append(
                        ClueSequence(
                            clue_number=clue_number,
                            question=clue.question,
                            location=f"Hide this at/with: {clue.answer}",
                            next_clue=f"{clue_number + 1}. {next_clue}",
                        )
                    )

                # Add the final clue (same for all groups)
                candidate_sequence.append(
                    ClueSequence(
                        clue_number=len(shuffled_clues) + 1,
                        question=final_clue.question,
                        location=f"Hide this at/with: {final_clue.answer}",
                        next_clue=f"{len(shuffled_clues) + 2}. The End",
                    )
                )

                sequence = candidate_sequence

                # Record constraints for this sequence (only for the randomizable part)
                self._record_constraints(shuffled_clues, used_first_clues, used_consecutive_pairs)

            if sequence is None:
                raise ValueError(f"Could not generate valid sequence for Group {group_num} after {max_attempts} attempts. Try using more clues or fewer groups.")

            all_sequences[group_num] = sequence

        return all_sequences

    def _violates_constraints(self, shuffled_clues: List[Clue], used_first_clues: set, used_consecutive_pairs: set) -> bool:
        """Check if a sequence violates constraints"""
        # Rule 1: No group can have the same first clue as another group
        if shuffled_clues[0].question in used_first_clues:
            return True

        # Rule 1b: First clue must always be a Place
        if shuffled_clues[0].clue_type and shuffled_clues[0].clue_type.lower() != 'place':
            return True

        # Rule 2: No two groups can share two sequential clues
        for i in range(len(shuffled_clues) - 1):
            pair = f"{shuffled_clues[i].question}|{shuffled_clues[i + 1].question}"
            if pair in used_consecutive_pairs:
                return True

        # Rule 3: Try to alternate Person and Place types
        if not self._follows_alternating_types(shuffled_clues):
            return True

        return False

    def _create_alternating_sequence(self, clues: List[Clue]) -> List[Clue]:
        """Create a sequence that tries to alternate between Person and Place types"""
        # Separate clues by type
        person_clues = [c for c in clues if c.clue_type and c.clue_type.lower() == 'person']
        place_clues = [c for c in clues if c.clue_type and c.clue_type.lower() == 'place']
        other_clues = [c for c in clues if not c.clue_type or c.clue_type.lower() not in ['person', 'place']]
        
        # If we don't have any place clues, return None (first clue must be Place)
        if len(place_clues) == 0:
            return None
            
        # If we don't have enough typed clues, return None to use random shuffle
        if len(person_clues) + len(place_clues) < 2:
            return None
            
        # Shuffle each type separately
        random.shuffle(person_clues)
        random.shuffle(place_clues)
        random.shuffle(other_clues)
        
        # Build alternating sequence
        result = []
        person_idx = 0
        place_idx = 0
        
        # REQUIREMENT: First clue must always be a Place
        current_type = 'place'
        
        # Create alternating sequence
        total_typed = len(person_clues) + len(place_clues)
        for i in range(total_typed):
            if current_type == 'place' and place_idx < len(place_clues):
                result.append(place_clues[place_idx])
                place_idx += 1
                current_type = 'person'
            elif current_type == 'person' and person_idx < len(person_clues):
                result.append(person_clues[person_idx])
                person_idx += 1
                current_type = 'place'
            elif place_idx < len(place_clues):
                result.append(place_clues[place_idx])
                place_idx += 1
                current_type = 'person'
            elif person_idx < len(person_clues):
                result.append(person_clues[person_idx])
                person_idx += 1
                current_type = 'place'
        
        # PREFERENCE: Try to make second-to-last clue a Place
        if len(result) >= 2:
            second_to_last_idx = len(result) - 2
            if (result[second_to_last_idx].clue_type and 
                result[second_to_last_idx].clue_type.lower() == 'person'):
                # Look for a Place clue to swap with
                for i in range(len(result) - 2):
                    if (result[i].clue_type and 
                        result[i].clue_type.lower() == 'place'):
                        # Swap to get Place as second-to-last
                        result[i], result[second_to_last_idx] = result[second_to_last_idx], result[i]
                        break
        
        # Add remaining other clues at random positions (but not first)
        for clue in other_clues:
            pos = random.randint(1, len(result))  # Start from position 1 to preserve Place-first
            result.insert(pos, clue)
            
        return result

    def _follows_alternating_types(self, shuffled_clues: List[Clue]) -> bool:
        """Check if the sequence alternates between Person and Place types where possible"""
        # If we don't have type information, don't enforce this constraint
        typed_clues = [clue for clue in shuffled_clues if clue.clue_type and clue.clue_type.lower() in ['person', 'place']]
        
        if len(typed_clues) < 2:
            return True  # Not enough typed clues to enforce alternation
        
        # Count violations of alternating pattern
        violations = 0
        for i in range(len(shuffled_clues) - 1):
            current_type = shuffled_clues[i].clue_type
            next_type = shuffled_clues[i + 1].clue_type
            
            # If both clues have types and they're the same, it's a violation
            if (current_type and next_type and 
                current_type.lower() in ['person', 'place'] and 
                next_type.lower() in ['person', 'place'] and
                current_type.lower() == next_type.lower()):
                violations += 1
        
        # Allow some flexibility - reject only if more than half the adjacent pairs are violations
        return violations <= len(shuffled_clues) // 2

    def _record_constraints(self, shuffled_clues: List[Clue], used_first_clues: set, used_consecutive_pairs: set):
        """Record constraints for a valid sequence"""
        # Record the first clue
        used_first_clues.add(shuffled_clues[0].question)

        # Record all consecutive pairs
        for i in range(len(shuffled_clues) - 1):
            pair = f"{shuffled_clues[i].question}|{shuffled_clues[i + 1].question}"
            used_consecutive_pairs.add(pair)

    def format_master_sheet(
        self, all_sequences: Dict[int, List[ClueSequence]]
    ) -> List[List[str]]:
        """Format data for the master sheet"""
        data = [["Group", "Clue Number", "Question", "Location", "Next Clue"]]

        for group_num, sequence in all_sequences.items():
            for clue_seq in sequence:
                data.append(
                    [
                        f"Group {group_num}",
                        str(clue_seq.clue_number),
                        clue_seq.question,
                        clue_seq.location,
                        clue_seq.next_clue,
                    ]
                )

        return data

    def format_group_sheet(
        self, group_num: int, sequence: List[ClueSequence]
    ) -> List[List[str]]:
        """Format data for an individual group sheet"""
        data = [["Location", "Clue"]]

        # First row: starting clue given to the group
        data.append([f"Group {group_num} First Clue", f"1. {sequence[0].question}"])

        # Subsequent rows: where to hide each clue and what clue will be found there
        for clue_seq in sequence:
            data.append([clue_seq.location, clue_seq.next_clue])

        return data


def main():
    """Main function to run the scavenger hunt generator"""
    parser = argparse.ArgumentParser(
        description="Generate scavenger hunt from Google Sheets",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--num_groups", type=int, required=True, help="Number of groups"
    )
    parser.add_argument(
        "--spreadsheet_name", type=str, help="Name of the Google Spreadsheet to find"
    )
    parser.add_argument(
        "--spreadsheet_id", type=str, help="ID of the Google Spreadsheet"
    )
    parser.add_argument(
        "--credentials_path", type=str, help="Path to Google credentials JSON file"
    )
    parser.add_argument(
        "--token_path", type=str, help="Path to store/load Google API token"
    )
    parser.add_argument(
        "--input_sheet",
        type=str,
        default="Clues",
        help="Name of the input sheet with clues",
    )
    parser.add_argument("--seed", type=int, help="Random seed for reproducible results")
    parser.add_argument(
        "--share",
        type=str,
        default="kevin@fink.com",
        help="Comma-separated list of email addresses to share with",
    )

    args = parser.parse_args()

    # Set random seed if provided
    if args.seed:
        random.seed(args.seed)

    # Validate arguments
    if not args.spreadsheet_name and not args.spreadsheet_id:
        print("Error: Must provide either --spreadsheet_name or --spreadsheet_id")
        sys.exit(1)

    # Initialize Google Sheets handler
    sheets_handler = GoogleSheetsHandler(
        credentials_path=args.credentials_path, token_path=args.token_path
    )

    try:
        # Find or use the spreadsheet
        created_new_spreadsheet = False
        if args.spreadsheet_id:
            spreadsheet_id = args.spreadsheet_id
        else:
            spreadsheet_id = sheets_handler.find_google_sheet(args.spreadsheet_name)
            if not spreadsheet_id:
                print(
                    f"Spreadsheet '{args.spreadsheet_name}' not found. Creating new spreadsheet..."
                )
                spreadsheet_id = sheets_handler.create_google_sheet(
                    args.spreadsheet_name
                )
                created_new_spreadsheet = True
                print(
                    f"Created new spreadsheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
                )

                # Create initial Clues sheet with sample data
                sample_clues = [
                    ["Clue", "Answer/Location/Person", "Type"],
                    ["What has keys but can't open locks?", "Piano", "Place"],
                    ["What has a face and two hands but no arms or legs?", "Clock", "Place"],
                    ["Who created this scavenger hunt?", "Kevin", "Person"],
                    ["Where do you cook your meals?", "Kitchen", "Place"],
                    ["Who is your favorite teacher?", "Mrs. Smith", "Person"],
                    ["What room has books but no bookshelf?", "Library", "Place"],
                    ["Where do cars sleep at night?", "Garage", "Place"],
                    ["Who can help you check out a book?", "Librarian", "Person"],
                    ["What's the coldest appliance in the house?", "Refrigerator", "Place"],
                    ["Where do you wash your hands before dinner?", "Bathroom sink", "Place"],
                ]
                sheets_handler.write_to_sheet(
                    spreadsheet_id, args.input_sheet, sample_clues
                )
                print(f"Created sample '{args.input_sheet}' sheet with example clues")

        print(
            f"Using spreadsheet: https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        )

        # Share the spreadsheet if it was newly created
        if created_new_spreadsheet and args.share:
            share_emails = [email.strip() for email in args.share.split(",")]
            print(f"Sharing spreadsheet with: {', '.join(share_emails)}")
            sheets_handler.share_google_sheet(spreadsheet_id, share_emails)

        # Check if the input sheet exists
        if not sheets_handler.sheet_exists(spreadsheet_id, args.input_sheet):
            print(
                f"Sheet '{args.input_sheet}' not found. Creating it with sample data..."
            )

            # Create the sheet with sample data
            sample_clues = [
                ["Clue", "Answer/Location/Person", "Type"],
                ["What has keys but can't open locks?", "Piano", "Place"],
                ["What has a face and two hands but no arms or legs?", "Clock", "Place"],
                ["Who created this scavenger hunt?", "Kevin", "Person"],
                ["Where do you cook your meals?", "Kitchen", "Place"],
                ["Who is your favorite teacher?", "Mrs. Smith", "Person"],
                ["What room has books but no bookshelf?", "Library", "Place"],
                ["Where do cars sleep at night?", "Garage", "Place"],
                ["Who can help you check out a book?", "Librarian", "Person"],
                ["What's the coldest appliance in the house?", "Refrigerator", "Place"],
                ["Where do you wash your hands before dinner?", "Bathroom sink", "Place"],
            ]
            sheets_handler.write_to_sheet(
                spreadsheet_id, args.input_sheet, sample_clues
            )

            print(f"\n✅ Created '{args.input_sheet}' sheet with sample data.")
            print(
                "📝 Please populate the sheet with your clues and run the script again."
            )
            print(
                f"🔗 Edit the spreadsheet here: https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
            )
            print("\nFormat: Column A = Clue/Question, Column B = Answer/Location/Person, Column C = Type (Person/Place)")
            sys.exit(0)

        # Read clues from the sheet
        print(f"Reading clues from sheet '{args.input_sheet}'...")
        clues = sheets_handler.read_clues_from_sheet(spreadsheet_id, args.input_sheet)
        print(f"Found {len(clues)} clues")

        # Generate the scavenger hunt
        print(f"Generating hunt for {args.num_groups} groups...")
        generator = ScavengerHuntGenerator(clues, args.num_groups)
        all_sequences = generator.generate_hunt()

        # Write master sheet
        print("Writing master sheet...")
        master_data = generator.format_master_sheet(all_sequences)
        sheets_handler.write_to_sheet(spreadsheet_id, "Master", master_data)

        # Write individual group sheets
        for group_num, sequence in all_sequences.items():
            print(f"Writing Group {group_num} sheet...")
            group_data = generator.format_group_sheet(group_num, sequence)
            sheets_handler.write_to_sheet(
                spreadsheet_id, f"Group {group_num}", group_data
            )

        print("\nScavenger hunt generated successfully!")
        print(f"View results: https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
        print("\nInstructions:")
        print("1. Print the 'Master' sheet for the hunt organizer")
        print("2. For each group sheet:")
        print("   - Print the sheet")
        print("   - Give the first row (first clue) to the group at the start")
        print(
            "   - Hide the remaining clues at the locations specified in the 'Location' column"
        )

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
