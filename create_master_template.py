import pandas as pd
import os

def create_master_template():
    columns = ["S.No.", "Roll No.", "Set No."] + [f"Q{i}" for i in range(1, 21)] + ["Objective Total"]
    
    # Create a writer
    with pd.ExcelWriter("master_template.xlsx", engine='openpyxl') as writer:
        df = pd.DataFrame(columns=columns)
        df.to_excel(writer, sheet_name="Objective-1", index=False)
        df.to_excel(writer, sheet_name="Objective-2", index=False)
        
    print("Created master_template.xlsx with Objective-1 and Objective-2 sheets.")

if __name__ == "__main__":
    create_master_template()
