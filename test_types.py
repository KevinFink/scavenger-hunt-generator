#!/usr/bin/env python3

import random
from scavenger_hunt_generator import Clue, ScavengerHuntGenerator

def test_alternating_types():
    """Test that the alternating type constraint works"""
    
    # Create test clues with better balance (3 Persons, 5 Places)
    clues = [
        Clue("Question 1", "Answer 1", "Person"),
        Clue("Question 2", "Answer 2", "Place"), 
        Clue("Question 3", "Answer 3", "Person"),
        Clue("Question 4", "Answer 4", "Place"),
        Clue("Question 5", "Answer 5", "Place"),
        Clue("Question 6", "Answer 6", "Person"),
        Clue("Question 7", "Answer 7", "Place"),
        Clue("Question 8", "Answer 8", "Place"),  # Final clue (Place)
    ]
    
    print("Test clues:")
    for i, clue in enumerate(clues):
        print(f"{i+1}. {clue.question} -> {clue.answer} ({clue.clue_type})")
    
    print("\n" + "="*50)
    
    # Set seed for reproducible results
    random.seed(42)
    
    # Generate hunt for 3 groups
    generator = ScavengerHuntGenerator(clues, 3)
    all_sequences = generator.generate_hunt()
    
    print(f"\nGenerated hunt for {len(all_sequences)} groups:\n")
    
    for group_num, sequence in all_sequences.items():
        print(f"Group {group_num} sequence:")
        types_sequence = []
        for i, clue_seq in enumerate(sequence):
            # Find the original clue to get its type
            original_clue = next(c for c in clues if c.question == clue_seq.question)
            types_sequence.append(original_clue.clue_type)
            print(f"  {i+1}. {clue_seq.question} ({original_clue.clue_type})")
        
        # Check alternation
        violations = 0
        for i in range(len(types_sequence) - 1):
            if types_sequence[i] == types_sequence[i+1]:
                violations += 1
                print(f"    ⚠️  Non-alternating: {types_sequence[i]} -> {types_sequence[i+1]}")
        
        if violations == 0:
            print("    ✅ Perfect alternation!")
        else:
            print(f"    ⚠️  {violations} violations (allowed: {len(types_sequence) // 2})")
        print()

if __name__ == "__main__":
    test_alternating_types()
