# Google Apps Script Setup

This document explains how to set up the Google Apps Script version of the Scavenger Hunt Generator.

## Setup Instructions

1. **Open your Google Sheet** (or create a new one)
2. **Go to Extensions → Apps Script**
3. **Replace the default code** with the contents of `scavenger_hunt_script.js`
4. **Save the script** (Ctrl+S or Cmd+S)
5. **Refresh your Google Sheet** (close and reopen, or refresh the browser)
6. **Look for the "Scavenger Hunt" menu** in the menu bar

## Usage

### Generate Hunt
1. Click **"Scavenger Hunt" → "Generate Hunt"**
2. **Enter the number of groups** when prompted
3. **If no clues exist**, you'll be offered to create sample clues automatically
4. **Review the generated sheets:**
   - **Master sheet:** Complete overview for organizers
   - **Group 1, Group 2, etc.:** Individual sheets for each group

### Create Sample Clues
1. Click **"Scavenger Hunt" → "Generate Sample Clues"**
2. **Confirm** if you want to replace existing clues
3. **Sample clues will be added** to the "Clues" sheet for you to edit

### Clear Hunt Sheets
1. Click **"Scavenger Hunt" → "Clear Hunt Sheets"**
2. **Confirm** to delete all Master and Group sheets
3. **Useful for cleanup** before generating a new hunt

### Clues Format
- **Column A:** Question/Clue
- **Column B:** Answer/Location/Person (where the next clue will be hidden)
- Edit the "Clues" sheet as needed before generating

## How It Works

The script creates a custom menu that:
- Reads clues from the "Clues" sheet (or creates sample clues if none exist)
- Generates randomized sequences for each group with constraints:
  - Each group gets a unique first clue
  - No two groups share consecutive clue pairs
  - **The last clue from the sheet is always the final clue for all groups**
- Creates a Master sheet with all sequences
- Creates individual group sheets with:
  - First clue to give to the group
  - Remaining clues and where to hide them

## Advantages Over Command Line

- **No installation required** - works entirely within Google Sheets
- **Easy sharing** - just share the Google Sheet
- **User-friendly** - simple menu interface
- **No authentication setup** - uses your existing Google account
- **Immediate results** - generates directly in the same spreadsheet

## Troubleshooting

- **No menu appears:** Refresh the sheet or check if the script was saved properly
- **Script errors:** Check the Apps Script editor for error messages
- **Permission issues:** You may need to authorize the script on first run
