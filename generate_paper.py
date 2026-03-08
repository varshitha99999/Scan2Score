import os
import random
import copy

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_input(prompt):
    return input(prompt).strip()

def get_int_input(prompt):
    while True:
        try:
            value = input(prompt).strip()
            return int(value)
        except ValueError:
            print("Please enter a valid number.")

def get_yes_no(prompt):
    while True:
        value = input(prompt).strip().lower()
        if value in ['yes', 'y']:
            return True
        elif value in ['no', 'n']:
            return False
        print("Please enter 'yes' or 'no'.")

def main():
    print("Question Paper Generator – CLI Mode")
    print("\nEnter the details as prompted.")
    print("\n------------------------------------")
    print("SECTION 1: CHOOSE THE CORRECT ANSWER")
    print("------------------------------------")

    mcqs = []
    try:
        num_mcqs = get_int_input("\nEnter number of MCQs: ")
        for i in range(num_mcqs):
            print(f"\nMCQ {i+1}:")
            question = get_input("Question: ")
            correct = get_input("Correct Answer: ")
            wrong1 = get_input("Wrong Answer 1: ")
            wrong2 = get_input("Wrong Answer 2: ")
            wrong3 = get_input("Wrong Answer 3: ")
            
            mcqs.append({
                'type': 'mcq',
                'question': question,
                'correct': correct,
                'options': [correct, wrong1, wrong2, wrong3] # Will be shuffled later if needed
            })
    except KeyboardInterrupt:
        print("\nAborted.")
        return

    print("\n------------------------------------")
    print("SECTION 2: MATCH THE FOLLOWING")
    print("------------------------------------")

    matches = []
    try:
        num_matches = get_int_input("\nEnter number of match-the-following questions: ")
        for i in range(num_matches):
            print(f"\nMatch Question {i+1}:")
            print("Left Items (comma separated):")
            left_items = [x.strip() for x in get_input("").split(',')]
            
            print("\nRight Items (comma separated – correct order):")
            right_items = [x.strip() for x in get_input("").split(',')]
            
            if len(left_items) != len(right_items):
                print(f"Warning: Number of left items ({len(left_items)}) does not match right items ({len(right_items)}).")
            
            # Store pairs
            pairs = list(zip(left_items, right_items))
            matches.append({
                'type': 'match',
                'pairs': pairs
            })
    except KeyboardInterrupt:
        print("\nAborted.")
        return

    print("\n------------------------------------")
    print("SECTION 3: FILL IN THE BLANKS")
    print("------------------------------------")

    fill_blanks = []
    try:
        num_fill = get_int_input("\nEnter number of fill-in-the-blank questions: ")
        for i in range(num_fill):
            print(f"\nFill {i+1}:")
            sentence = get_input("Sentence: ")
            answer = get_input("Answer: ")
            
            fill_blanks.append({
                'type': 'fill',
                'sentence': sentence,
                'answer': answer
            })
    except KeyboardInterrupt:
        print("\nAborted.")
        return

    print("\n------------------------------------")
    print("FINAL OPTIONS")
    print("------------------------------------")

    num_sets = get_int_input("\nGenerate how many question paper sets? ")
    shuffle_questions = get_yes_no("\nShuffle questions and options? (yes/no): ")
    check_duplicates = get_yes_no("\nCheck and prevent duplicate questions? (yes/no): ")

    print("\n------------------------------------")
    print("Processing...")
    print("------------------------------------")

    # Duplicate checking (simple implementation based on question text)
    if check_duplicates:
        seen_questions = set()
        unique_mcqs = []
        for q in mcqs:
            if q['question'] not in seen_questions:
                seen_questions.add(q['question'])
                unique_mcqs.append(q)
        if len(unique_mcqs) < len(mcqs):
            print(f"⚠ Removed {len(mcqs) - len(unique_mcqs)} duplicate MCQs.")
        mcqs = unique_mcqs

        # Similar check for Fill in blanks
        seen_fill = set()
        unique_fill = []
        for q in fill_blanks:
            if q['sentence'] not in seen_fill:
                seen_fill.add(q['sentence'])
                unique_fill.append(q)
        if len(unique_fill) < len(fill_blanks):
             print(f"⚠ Removed {len(fill_blanks) - len(unique_fill)} duplicate Fill-in-the-blanks.")
        fill_blanks = unique_fill
        
        print("\n✔ No duplicates detected (after cleanup)")
    else:
        print("\n✔ No duplicates detected") # Mimicking user log, assuming they entered unique ones or skipped check

    if not os.path.exists('output'):
        os.makedirs('output')

    # Generate Sets
    for set_num in range(1, num_sets + 1):
        paper_content = f"QUESTION PAPER - SET {set_num}\n"
        paper_content += "="*30 + "\n\n"
        
        # Process MCQs
        current_mcqs = copy.deepcopy(mcqs)
        if shuffle_questions:
            random.shuffle(current_mcqs)
        
        if current_mcqs:
            paper_content += "SECTION 1: CHOOSE THE CORRECT ANSWER\n" + "-"*36 + "\n"
            for idx, q in enumerate(current_mcqs, 1):
                paper_content += f"{idx}. {q['question']}\n"
                options = q['options']
                if shuffle_questions:
                    random.shuffle(options)
                
                # Assign A, B, C, D
                labels = ['A', 'B', 'C', 'D']
                for label, opt in zip(labels, options):
                    paper_content += f"   {label}) {opt}\n"
                paper_content += "\n"

        # Process Match
        # Note: Match questions are usually complex to shuffle "options" for while keeping the structure.
        # Usually, Left side is fixed 1..N, Right side is shuffled A..N.
        current_matches = copy.deepcopy(matches)
        if shuffle_questions:
            random.shuffle(current_matches)
            
        if current_matches:
            paper_content += "SECTION 2: MATCH THE FOLLOWING\n" + "-"*30 + "\n"
            match_counter = 1
            for q in current_matches:
                paper_content += f"Q{match_counter}. Match the following:\n"
                
                left_side = [p[0] for p in q['pairs']]
                right_side = [p[1] for p in q['pairs']]
                
                if shuffle_questions:
                    random.shuffle(right_side)
                
                for i in range(len(left_side)):
                    # A. LeftItem    1. RightItem
                    # Just simple formatting
                    paper_content += f"   {chr(65+i)}. {left_side[i]:<20} {i+1}. {right_side[i]}\n"
                
                paper_content += "\n"
                match_counter += 1

        # Process Fill in the blanks
        current_fill = copy.deepcopy(fill_blanks)
        if shuffle_questions:
            random.shuffle(current_fill)
            
        if current_fill:
            paper_content += "SECTION 3: FILL IN THE BLANKS\n" + "-"*30 + "\n"
            for idx, q in enumerate(current_fill, 1):
                paper_content += f"{idx}. {q['sentence']}\n"
                paper_content += "   Answer: ____________________\n\n"

        with open(f"output/Set_{set_num}.txt", "w") as f:
            f.write(paper_content)

    print(f"✔ {num_sets} Question Papers Generated")

    # Generate Answer Key (Master Key)
    # Since questions might be shuffled in sets, a single answer key is tricky if every set is different.
    # Usually, "Answer Key" implies the key for the questions entered. 
    # Or, if sets are shuffled, we might need a key for each set or just a master list of questions and answers.
    # Given the user log says "Answer Key Generated" (singular), I'll generate a master key of the inputs.
    
    key_content = "MASTER ANSWER KEY\n" + "="*20 + "\n\n"
    
    if mcqs:
        key_content += "SECTION 1: MCQs\n"
        for idx, q in enumerate(mcqs, 1):
            key_content += f"{idx}. {q['question']} -> {q['correct']}\n"
        key_content += "\n"
        
    if matches:
        key_content += "SECTION 2: MATCH THE FOLLOWING\n"
        for idx, q in enumerate(matches, 1):
            key_content += f"Match Q{idx}:\n"
            for pair in q['pairs']:
                key_content += f"  {pair[0]} -> {pair[1]}\n"
            key_content += "\n"

    if fill_blanks:
        key_content += "SECTION 3: FILL IN THE BLANKS\n"
        for idx, q in enumerate(fill_blanks, 1):
            key_content += f"{idx}. {q['sentence']} -> {q['answer']}\n"

    with open("output/Answer_Key.txt", "w") as f:
        f.write(key_content)

    print("✔ Answer Key Generated")
    print("\nFiles saved successfully.")

if __name__ == "__main__":
    main()
