# Scavenger Hunt Generator

Create a system that will facilitate the generation of scavenger hunts, intended for groups of people to compete to
find the "locations" pointed to by clues as fast as possible.

## Setup

### Option 1: Google Apps Script (Recommended)
For the easiest setup, use the Google Apps Script version that runs directly in Google Sheets:

1. See [APPS_SCRIPT_SETUP.md](APPS_SCRIPT_SETUP.md) for detailed instructions
2. Copy the code from `scavenger_hunt_script.js` into Google Apps Script
3. No installation required - works entirely within Google Sheets!

### Option 2: Command Line (Python)
For command line usage:

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Install pre-commit hooks:
   ```bash
   poetry run pre-commit install
   ```

A hunt will be built based on a set of clues and locations. Each clue will lead to a location where the next clue can
be found.  The location may be a physical location, or it may be a person who will give the next clue when asked.

The clues will be written on slips of paper, each (except the first) hidden at the location indicated by the previous
clue.

A typical hunt will contain 10-20 clues.  The groups will contain 2-5 people -- the number of groups should be a
parameter (--num_groups).

The clues will be given in a random order to each group, so that they can't just follow another group around. The first
clue will be given to each group, and they will have to find the next clue based on the answer to the previous clue.

The last clue from the Clues sheet will be the same for every group, and will lead to a final location where the hunt ends.

Each clue will be numbered, and that number will appear on the next clue, so that the group knows they are on the right
track. If they find a clue with the wrong number, they know they found the wrong one, and should keep looking.

If there are N groups, the system will generate N sets of (clue, answer, next clue), with each clue appearing once in
the first element and once in the third.

As a simple example, if the clue list is:
Clue, Answer
"What has keys but can't open locks?", "A piano"
"What has a face and two hands but no arms or legs?", "A clock"
"Who created this scavenger hunt?", "Kevin"

Then for 2 groups, the system would generate:
Group 1:
G1C1: What has keys but can't open locks?, (Hide this in the piano), 1. "What has a face and two hands but no arms or legs?"
G1C2. What has a face and two hands but no arms or legs?, (Hide this in the clock), 2. "Who created this scavenger hunt?"
G1C3. Who created this scavenger hunt?, (Hide this with Kevin), 3. "The End"

Group 2:
G2C1. What has a face and two hands but no arms or legs?, (Hide this in the clock), 1. "What has keys but can't open locks?"
G2C2. What has keys but can't open locks?, (Hide this in the piano), 2. "Who created this scavenger hunt?"
G2C3. Who created this scavenger hunt?, (Hide this with Kevin), 3. "The End"

The input will be a Google Sheet with a sheet named "Clues" and the output will be additional sheets: one master sheet
and one sheet per group. The master sheet should have the full generated hunt, organized by group and clue number. Each
group sheet should have the clues for that group, in order, along with where that clue should be hidden (the second
and third columns from above). The first row just has the first clue. The group sheets will be cut apart, the first
row kept to give to the group at the start of the hunt, and the rest hidden at the indicated locations before the hunt
starts.
