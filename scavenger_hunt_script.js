/**
 * Google Apps Script for Scavenger Hunt Generator
 * 
 * To use:
 * 1. Open your Google Sheet
 * 2. Go to Extensions → Apps Script
 * 3. Replace the default code with this script
 * 4. Save and refresh your Google Sheet
 * 5. A "Scavenger Hunt" menu will appear
 */

/**
 * Creates custom menu when the spreadsheet opens
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('Scavenger Hunt')
    .addItem('Generate Hunt', 'generateScavengerHunt')
    .addSeparator()
    .addItem('Generate Sample Clues', 'createSampleClues')
    .addItem('Clear Hunt Sheets', 'clearHuntSheets')
    .addToUi();
}

/**
 * Main function to generate scavenger hunt
 */
function generateScavengerHunt() {
  const ui = SpreadsheetApp.getUi();
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  
  try {
    // Get number of groups from user
    const numGroupsResponse = ui.prompt(
      'Generate Scavenger Hunt',
      'How many groups will participate?',
      ui.ButtonSet.OK_CANCEL
    );
    
    if (numGroupsResponse.getSelectedButton() !== ui.Button.OK) {
      return;
    }
    
    const numGroups = parseInt(numGroupsResponse.getResponseText());
    if (isNaN(numGroups) || numGroups < 1 || numGroups > 20) {
      ui.alert('Please enter a valid number of groups (1-20)');
      return;
    }
    
    // Read clues from the Clues sheet
    let clues = readCluesFromSheet(spreadsheet);
    if (clues.length === 0) {
      // Offer to create sample clues
      const response = ui.alert(
        'No Clues Found',
        'No clues found in the "Clues" sheet. Would you like to create sample clues to get started?',
        ui.ButtonSet.YES_NO
      );
      
      if (response === ui.Button.YES) {
        createSampleClues(spreadsheet);
        clues = readCluesFromSheet(spreadsheet);
      } else {
        ui.alert('Please add clues to the "Clues" sheet first.');
        return;
      }
    }
    
    // Clean up any existing hunt sheets
    cleanupExistingHuntSheets(spreadsheet);
    
    // Generate hunt sequences
    const allSequences = generateHuntSequences(clues, numGroups);
    
    // Create Master sheet
    createMasterSheet(spreadsheet, allSequences);
    
    // Create individual group sheets
    for (let groupNum = 1; groupNum <= numGroups; groupNum++) {
      createGroupSheet(spreadsheet, groupNum, allSequences[groupNum]);
    }
    
    ui.alert(
      `Success!`,
      `Scavenger hunt generated for ${numGroups} groups!\n\n` +
      `Sheets created:\n` +
      `• Master sheet (for organizers)\n` +
      `• Group 1 through Group ${numGroups} (for participants)\n\n` +
      `Instructions:\n` +
      `1. Print the Master sheet for reference\n` +
      `2. Give each group their first clue (row 2 of their sheet)\n` +
      `3. Hide the remaining clues at the specified locations`,
      ui.ButtonSet.OK
    );
    
  } catch (error) {
    ui.alert('Error', `Failed to generate hunt: ${error.message}`, ui.ButtonSet.OK);
    console.error('Error generating hunt:', error);
  }
}

/**
 * Read clues from the Clues sheet
 */
function readCluesFromSheet(spreadsheet) {
  let cluesSheet;
  try {
    cluesSheet = spreadsheet.getSheetByName('Clues');
  } catch (e) {
    throw new Error('Clues sheet not found. Please create a sheet named "Clues" with your clues.');
  }
  
  const range = cluesSheet.getDataRange();
  const values = range.getValues();
  
  if (values.length === 0) {
    return [];
  }
  
  const clues = [];
  let startRow = 0;
  
  // Skip header row if present
  if (values[0] && values[0].length >= 2) {
    const firstCell = values[0][0].toString().toLowerCase();
    if (firstCell === 'clue' || firstCell === 'question') {
      startRow = 1;
    }
  }
  
  for (let i = startRow; i < values.length; i++) {
    const row = values[i];
    if (row.length >= 2 && row[0] && row[1]) {
      const clueType = row.length >= 3 && row[2] ? row[2].toString().trim() : null;
      clues.push({
        question: row[0].toString().trim(),
        answer: row[1].toString().trim(),
        clueType: clueType
      });
    }
  }
  
  return clues;
}

/**
 * Generate hunt sequences for all groups with constraints
 */
function generateHuntSequences(clues, numGroups) {
  if (clues.length < 2) {
    throw new Error('Need at least 2 clues to generate a hunt');
  }
  
  const allSequences = {};
  const usedFirstClues = new Set();
  const usedConsecutivePairs = new Set();
  
  // Reserve the last clue as the final clue for all groups
  const finalClue = clues[clues.length - 1];
  const randomizableClues = clues.slice(0, -1);
  
  for (let groupNum = 1; groupNum <= numGroups; groupNum++) {
    let sequence = null;
    let attempts = 0;
    const maxAttempts = 100; // Prevent infinite loops
    
    // Keep trying until we find a valid sequence
    while (sequence === null && attempts < maxAttempts) {
      attempts++;
      
      // Try to create a sequence that alternates types when possible
      let shuffledClues = createAlternatingSequence(randomizableClues);
      
      // If alternating didn't work well, fall back to random shuffle
      if (shuffledClues === null || violatesConstraints(shuffledClues, usedFirstClues, usedConsecutivePairs)) {
        shuffledClues = [...randomizableClues];
        shuffleArray(shuffledClues);
        
        // Check if this sequence violates constraints
        if (violatesConstraints(shuffledClues, usedFirstClues, usedConsecutivePairs)) {
          continue; // Try again with a different shuffle
        }
      }
      
      // Create sequence for this group (randomizable clues + final clue)
      const candidateSequence = [];
      
      // Add the randomizable clues
      for (let i = 0; i < shuffledClues.length; i++) {
        const clue = shuffledClues[i];
        const clueNumber = i + 1;
        
        // Determine the next clue
        let nextClue;
        if (i < shuffledClues.length - 1) {
          nextClue = `Group ${groupNum} Clue ${clueNumber + 1}. ${shuffledClues[i + 1].question}`;
        } else {
          // Next clue is the final clue
          nextClue = `Group ${groupNum} Clue ${clueNumber + 1}. ${finalClue.question}`;
        }
        
        candidateSequence.push({
          clueNumber: clueNumber,
          question: clue.question,
          location: `Hide this at/with: ${clue.answer}`,
          nextClue: nextClue
        });
      }
      
      // Add the final clue (same for all groups)
      candidateSequence.push({
        clueNumber: shuffledClues.length + 1,
        question: finalClue.question,
        location: `Hide this at/with: ${finalClue.answer}`,
        nextClue: `${shuffledClues.length + 2}. The End`
      });
      
      sequence = candidateSequence;
      
      // Record constraints for this sequence (only for the randomizable part)
      recordConstraints(shuffledClues, usedFirstClues, usedConsecutivePairs);
    }
    
    if (sequence === null) {
      throw new Error(`Could not generate valid sequence for Group ${groupNum} after ${maxAttempts} attempts. Try using more clues or fewer groups.`);
    }
    
    allSequences[groupNum] = sequence;
  }
  
  return allSequences;
}

/**
 * Create a sequence that tries to alternate between Person and Place types
 */
function createAlternatingSequence(clues) {
  // Separate clues by type
  const personClues = clues.filter(c => c.clueType && c.clueType.toLowerCase() === 'person');
  const placeClues = clues.filter(c => c.clueType && c.clueType.toLowerCase() === 'place');
  const otherClues = clues.filter(c => !c.clueType || !['person', 'place'].includes(c.clueType.toLowerCase()));
  
  // If we don't have any place clues, return null (first clue must be Place)
  if (placeClues.length === 0) {
    return null;
  }
  
  // If we don't have enough typed clues, return null to use random shuffle
  if (personClues.length + placeClues.length < 2) {
    return null;
  }
  
  // Shuffle each type separately
  shuffleArray(personClues);
  shuffleArray(placeClues);
  shuffleArray(otherClues);
  
  // Build alternating sequence
  const result = [];
  let personIdx = 0;
  let placeIdx = 0;
  
  // REQUIREMENT: First clue must always be a Place
  let currentType = 'place';
  
  // Create alternating sequence
  const totalTyped = personClues.length + placeClues.length;
  for (let i = 0; i < totalTyped; i++) {
    if (currentType === 'place' && placeIdx < placeClues.length) {
      result.push(placeClues[placeIdx]);
      placeIdx++;
      currentType = 'person';
    } else if (currentType === 'person' && personIdx < personClues.length) {
      result.push(personClues[personIdx]);
      personIdx++;
      currentType = 'place';
    } else if (placeIdx < placeClues.length) {
      result.push(placeClues[placeIdx]);
      placeIdx++;
      currentType = 'person';
    } else if (personIdx < personClues.length) {
      result.push(personClues[personIdx]);
      personIdx++;
      currentType = 'place';
    }
  }
  
  // PREFERENCE: Try to make second-to-last clue a Place
  if (result.length >= 2) {
    const secondToLastIdx = result.length - 2;
    if (result[secondToLastIdx].clueType && 
        result[secondToLastIdx].clueType.toLowerCase() === 'person') {
      // Look for a Place clue to swap with
      for (let i = 0; i < result.length - 2; i++) {
        if (result[i].clueType && 
            result[i].clueType.toLowerCase() === 'place') {
          // Swap to get Place as second-to-last
          [result[i], result[secondToLastIdx]] = [result[secondToLastIdx], result[i]];
          break;
        }
      }
    }
  }
  
  // Add remaining other clues at random positions (but not first)
  for (const clue of otherClues) {
    const pos = Math.floor(Math.random() * result.length) + 1; // Start from position 1 to preserve Place-first
    result.splice(pos, 0, clue);
  }
  
  return result;
}

/**
 * Check if the sequence alternates between Person and Place types where possible
 */
function followsAlternatingTypes(shuffledClues) {
  // If we don't have type information, don't enforce this constraint
  const typedClues = shuffledClues.filter(clue => 
    clue.clueType && ['person', 'place'].includes(clue.clueType.toLowerCase()));
  
  if (typedClues.length < 2) {
    return true; // Not enough typed clues to enforce alternation
  }
  
  // Count violations of alternating pattern
  let violations = 0;
  for (let i = 0; i < shuffledClues.length - 1; i++) {
    const currentType = shuffledClues[i].clueType;
    const nextType = shuffledClues[i + 1].clueType;
    
    // If both clues have types and they're the same, it's a violation
    if (currentType && nextType &&
        ['person', 'place'].includes(currentType.toLowerCase()) &&
        ['person', 'place'].includes(nextType.toLowerCase()) &&
        currentType.toLowerCase() === nextType.toLowerCase()) {
      violations++;
    }
  }
  
  // Allow some flexibility - reject only if more than half the adjacent pairs are violations
  return violations <= Math.floor(shuffledClues.length / 2);
}

/**
 * Check if a sequence violates constraints
 */
function violatesConstraints(shuffledClues, usedFirstClues, usedConsecutivePairs) {
  // Rule 1: No group can have the same first clue as another group
  if (usedFirstClues.has(shuffledClues[0].question)) {
    return true;
  }
  
  // Rule 1b: First clue must always be a Place
  if (shuffledClues[0].clueType && shuffledClues[0].clueType.toLowerCase() !== 'place') {
    return true;
  }
  
  // Rule 2: No two groups can share two sequential clues
  for (let i = 0; i < shuffledClues.length - 1; i++) {
    const pair = `${shuffledClues[i].question}|${shuffledClues[i + 1].question}`;
    if (usedConsecutivePairs.has(pair)) {
      return true;
    }
  }
  
  // Rule 3: Try to alternate Person and Place types
  if (!followsAlternatingTypes(shuffledClues)) {
    return true;
  }
  
  return false;
}

/**
 * Record constraints for a valid sequence
 */
function recordConstraints(shuffledClues, usedFirstClues, usedConsecutivePairs) {
  // Record the first clue
  usedFirstClues.add(shuffledClues[0].question);
  
  // Record all consecutive pairs
  for (let i = 0; i < shuffledClues.length - 1; i++) {
    const pair = `${shuffledClues[i].question}|${shuffledClues[i + 1].question}`;
    usedConsecutivePairs.add(pair);
  }
}

/**
 * Clear hunt sheets - menu function for users
 */
function clearHuntSheets() {
  const ui = SpreadsheetApp.getUi();
  const spreadsheet = SpreadsheetApp.getActiveSpreadsheet();
  
  const response = ui.alert(
    'Clear Hunt Sheets',
    'This will delete all Master and Group sheets. Are you sure?',
    ui.ButtonSet.YES_NO
  );
  
  if (response === ui.Button.YES) {
    cleanupExistingHuntSheets(spreadsheet);
    ui.alert('Hunt sheets cleared successfully!');
  }
}

/**
 * Clean up any existing hunt sheets (Master and all Group sheets)
 */
function cleanupExistingHuntSheets(spreadsheet) {
  const sheets = spreadsheet.getSheets();
  
  for (const sheet of sheets) {
    const sheetName = sheet.getName();
    
    // Delete Master sheet
    if (sheetName === 'Master') {
      spreadsheet.deleteSheet(sheet);
      continue;
    }
    
    // Delete any Group sheets (Group 1, Group 2, etc.)
    if (sheetName.match(/^Group \d+$/)) {
      spreadsheet.deleteSheet(sheet);
    }
  }
}

/**
 * Shuffle array in place using Fisher-Yates algorithm
 */
function shuffleArray(array) {
  for (let i = array.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [array[i], array[j]] = [array[j], array[i]];
  }
}

/**
 * Create the Master sheet
 */
function createMasterSheet(spreadsheet, allSequences) {
  // Create new Master sheet
  const masterSheet = spreadsheet.insertSheet('Master');
  
  // Prepare data
  const data = [['Group', 'Clue Number', 'Question', 'Location', 'Next Clue']];
  
  for (const [groupNum, sequence] of Object.entries(allSequences)) {
    for (const clueSeq of sequence) {
      data.push([
        `Group ${groupNum}`,
        clueSeq.clueNumber,
        clueSeq.question,
        clueSeq.location,
        clueSeq.nextClue
      ]);
    }
  }
  
  // Write data to sheet
  const range = masterSheet.getRange(1, 1, data.length, data[0].length);
  range.setValues(data);
  
  // Format the header row
  const headerRange = masterSheet.getRange(1, 1, 1, data[0].length);
  headerRange.setFontWeight('bold');
  headerRange.setBackground('#4285f4');
  headerRange.setFontColor('white');
  
  // Auto-resize columns
  masterSheet.autoResizeColumns(1, data[0].length);
}

/**
 * Create an individual group sheet
 */
function createGroupSheet(spreadsheet, groupNum, sequence) {
  const sheetName = `Group ${groupNum}`;
  
  // Create new group sheet
  const groupSheet = spreadsheet.insertSheet(sheetName);
  
  // Prepare data
  const data = [['Location', 'Clue']];
  
  // First row: starting clue given to the group
  data.push([`Group ${groupNum} First Clue`, `Group ${groupNum} Clue 1. ${sequence[0].question}`]);
  
  // Subsequent rows: where to hide each clue and what clue will be found there
  for (const clueSeq of sequence) {
    data.push([clueSeq.location, clueSeq.nextClue]);
  }
  
  // Write data to sheet
  const range = groupSheet.getRange(1, 1, data.length, data[0].length);
  range.setValues(data);
  
  // Format the header row
  const headerRange = groupSheet.getRange(1, 1, 1, data[0].length);
  headerRange.setFontWeight('bold');
  headerRange.setBackground('#34a853');
  headerRange.setFontColor('white');
  
  // Format the first clue row (for the group)
  const firstClueRange = groupSheet.getRange(2, 1, 1, data[0].length);
  firstClueRange.setBackground('#fff2cc');
  firstClueRange.setFontWeight('bold');
  
  // Auto-resize columns
  groupSheet.autoResizeColumns(1, data[0].length);
}

/**
 * Create sample clues for testing
 */
function createSampleClues(spreadsheet) {
  spreadsheet = spreadsheet || SpreadsheetApp.getActiveSpreadsheet();
  const ui = SpreadsheetApp.getUi();
  
  try {
    // Check if Clues sheet exists
    let cluesSheet = spreadsheet.getSheetByName('Clues');
    
    if (cluesSheet) {
      const response = ui.alert(
        'Clues Sheet Exists',
        'A "Clues" sheet already exists. Replace it with sample clues?',
        ui.ButtonSet.YES_NO
      );
      if (response !== ui.Button.YES) {
        return;
      }
      
      // Clear existing content instead of deleting (can't delete the only sheet)
      cluesSheet.clear();
    } else {
      // Create new Clues sheet
      cluesSheet = spreadsheet.insertSheet('Clues');
    }
    
    // Sample clues data
    const sampleData = [
      ['Clue', 'Answer/Location/Person', 'Type'],
      ['What has keys but can\'t open locks?', 'Piano', 'Place'],
      ['What has a face and two hands but no arms or legs?', 'Clock', 'Place'],
      ['Who created this scavenger hunt?', 'Kevin', 'Person'],
      ['Where do you cook your meals?', 'Kitchen', 'Place'],
      ['Who is your favorite teacher?', 'Mrs. Smith', 'Person'],
      ['What room has books but no bookshelf?', 'Library', 'Place'],
      ['Where do cars sleep at night?', 'Garage', 'Place'],
      ['Who can help you check out a book?', 'Librarian', 'Person'],
      ['What\'s the coldest appliance in the house?', 'Refrigerator', 'Place'],
      ['Where do you wash your hands before dinner?', 'Bathroom sink', 'Place']
    ];
    
    // Write sample data
    const range = cluesSheet.getRange(1, 1, sampleData.length, sampleData[0].length);
    range.setValues(sampleData);
    
    // Format the header row
    const headerRange = cluesSheet.getRange(1, 1, 1, sampleData[0].length);
    headerRange.setFontWeight('bold');
    headerRange.setBackground('#ff9900');
    headerRange.setFontColor('white');
    
    // Auto-resize columns
    cluesSheet.autoResizeColumns(1, sampleData[0].length);
    
    ui.alert(
      'Sample Clues Created',
      'Sample clues have been added to the "Clues" sheet.\n\n' +
      'Format: Column A = Clue/Question, Column B = Answer/Location/Person, Column C = Type (Person/Place)\n\n' +
      'Edit the clues as needed, then use "Generate Hunt" to create your scavenger hunt.',
      ui.ButtonSet.OK
    );
    
  } catch (error) {
    ui.alert('Error', `Failed to create sample clues: ${error.message}`, ui.ButtonSet.OK);
    console.error('Error creating sample clues:', error);
  }
}
