"""
Excel Matcher for Roll Number Detection
======================================
Handles matching detected roll numbers with student records in Excel files.
"""

import os
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher
import re


@dataclass
class MatchResult:
    """Result of Excel matching operation"""
    match_found: bool
    row_number: Optional[int]
    similarity_score: float
    candidate_matches: List[str]
    matched_roll_number: Optional[str]


class ExcelMatcher:
    """
    Handles matching detected roll numbers with existing Excel records.
    """
    
    def __init__(self, excel_path: str, config: Dict = None):
        """
        Initialize Excel matcher.
        
        Args:
            excel_path: Path to the Excel file
            config: Configuration dictionary
        """
        self.excel_path = excel_path
        self.config = config or self._default_config()
        self.df = None
        self.roll_number_column = None
        self._load_excel()
    
    def _default_config(self) -> Dict:
        """Default configuration for Excel matching"""
        return {
            'fuzzy_match_threshold': 0.9,
            'roll_number_columns': ['Roll No', 'Roll Number', 'RollNo', 'Student ID', 'ID'],
            'case_sensitive': False,
            'exact_match_priority': True,
            'max_candidates': 5
        }
    
    def _load_excel(self):
        """Load Excel file and identify roll number column"""
        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(f"Excel file not found: {self.excel_path}")
        
        try:
            # Try different sheet names for the exam type
            sheet_names = None
            if self.excel_path.endswith('.xlsx') or self.excel_path.endswith('.xls'):
                excel_file = pd.ExcelFile(self.excel_path)
                sheet_names = excel_file.sheet_names
            
            # Load the appropriate sheet
            if sheet_names:
                # Look for sheets with "Objective" in the name first
                target_sheet = None
                for sheet in sheet_names:
                    if 'objective' in sheet.lower():
                        target_sheet = sheet
                        break
                
                if target_sheet:
                    self.df = pd.read_excel(self.excel_path, sheet_name=target_sheet)
                else:
                    self.df = pd.read_excel(self.excel_path, sheet_name=0)  # First sheet
            else:
                self.df = pd.read_csv(self.excel_path)
            
            # Find roll number column
            self._identify_roll_number_column()
            
        except Exception as e:
            raise RuntimeError(f"Failed to load Excel file: {str(e)}")
    
    def _identify_roll_number_column(self):
        """Identify which column contains roll numbers"""
        for col_name in self.config['roll_number_columns']:
            # Check exact match first
            if col_name in self.df.columns:
                self.roll_number_column = col_name
                return
            
            # Check case-insensitive match
            for actual_col in self.df.columns:
                if col_name.lower() in str(actual_col).lower():
                    self.roll_number_column = actual_col
                    return
        
        # If no standard column found, look for patterns
        for col in self.df.columns:
            col_str = str(col).lower()
            if any(keyword in col_str for keyword in ['roll', 'student', 'id', 'number']):
                self.roll_number_column = col
                return
        
        raise ValueError("Could not identify roll number column in Excel file")
    
    def find_student_record(self, roll_number: str) -> MatchResult:
        """
        Find matching student record in Excel.
        
        Args:
            roll_number: The roll number to search for
            
        Returns:
            MatchResult with match information
        """
        if self.df is None or self.roll_number_column is None:
            return MatchResult(
                match_found=False,
                row_number=None,
                similarity_score=0.0,
                candidate_matches=[],
                matched_roll_number=None
            )
        
        cleaned_roll = self._clean_roll_number(roll_number)
        
        # Get all existing roll numbers
        existing_rolls = self.get_existing_roll_numbers()
        
        # Try exact match first
        exact_matches = self._find_exact_matches(cleaned_roll, existing_rolls)
        if exact_matches:
            match_roll, row_idx = exact_matches[0]
            return MatchResult(
                match_found=True,
                row_number=row_idx,
                similarity_score=1.0,
                candidate_matches=[match_roll],
                matched_roll_number=match_roll
            )
        
        # Try fuzzy matching
        fuzzy_matches = self._find_fuzzy_matches(cleaned_roll, existing_rolls)
        if fuzzy_matches:
            best_match = fuzzy_matches[0]
            match_roll, similarity, row_idx = best_match
            
            candidates = [match[0] for match in fuzzy_matches[:self.config['max_candidates']]]
            
            return MatchResult(
                match_found=similarity >= self.config['fuzzy_match_threshold'],
                row_number=row_idx if similarity >= self.config['fuzzy_match_threshold'] else None,
                similarity_score=similarity,
                candidate_matches=candidates,
                matched_roll_number=match_roll if similarity >= self.config['fuzzy_match_threshold'] else None
            )
        
        return MatchResult(
            match_found=False,
            row_number=None,
            similarity_score=0.0,
            candidate_matches=[],
            matched_roll_number=None
        )
    
    def fuzzy_match(self, roll_number: str, threshold: float = None) -> List[MatchResult]:
        """Find similar roll numbers using fuzzy matching"""
        if threshold is None:
            threshold = self.config['fuzzy_match_threshold']
        
        cleaned_roll = self._clean_roll_number(roll_number)
        existing_rolls = self.get_existing_roll_numbers()
        
        fuzzy_matches = self._find_fuzzy_matches(cleaned_roll, existing_rolls)
        
        results = []
        for match_roll, similarity, row_idx in fuzzy_matches:
            if similarity >= threshold:
                results.append(MatchResult(
                    match_found=True,
                    row_number=row_idx,
                    similarity_score=similarity,
                    candidate_matches=[match_roll],
                    matched_roll_number=match_roll
                ))
        
        return results
    
    def get_existing_roll_numbers(self) -> List[str]:
        """Extract all existing roll numbers from Excel"""
        if self.df is None or self.roll_number_column is None:
            return []
        
        roll_numbers = []
        for value in self.df[self.roll_number_column].dropna():
            cleaned = self._clean_roll_number(str(value))
            if cleaned:
                roll_numbers.append(cleaned)
        
        return roll_numbers
    
    def add_student_record(self, roll_number: str, student_data: Dict = None) -> int:
        """
        Add a new student record to the Excel data.
        
        Args:
            roll_number: The roll number to add
            student_data: Additional student data
            
        Returns:
            Row index of the added record
        """
        if self.df is None:
            raise RuntimeError("Excel data not loaded")
        
        # Create new row data
        new_row = {self.roll_number_column: roll_number}
        if student_data:
            new_row.update(student_data)
        
        # Add to dataframe
        new_row_df = pd.DataFrame([new_row])
        self.df = pd.concat([self.df, new_row_df], ignore_index=True)
        
        return len(self.df) - 1
    
    def get_student_data(self, row_number: int) -> Dict:
        """Get all data for a student at the given row"""
        if self.df is None or row_number >= len(self.df):
            return {}
        
        return self.df.iloc[row_number].to_dict()
    
    def update_student_marks(self, row_number: int, marks_data: Dict):
        """Update marks for a student at the given row"""
        if self.df is None or row_number >= len(self.df):
            return False
        
        for column, value in marks_data.items():
            if column in self.df.columns:
                self.df.at[row_number, column] = value
        
        return True
    
    def save_excel(self, output_path: str = None):
        """Save the updated Excel file"""
        if self.df is None:
            return False
        
        save_path = output_path or self.excel_path
        
        try:
            if save_path.endswith('.csv'):
                self.df.to_csv(save_path, index=False)
            else:
                self.df.to_excel(save_path, index=False)
            return True
        except Exception as e:
            print(f"Error saving Excel file: {e}")
            return False
    
    def _clean_roll_number(self, roll_number: str) -> str:
        """Clean and normalize roll number for matching"""
        if not roll_number or pd.isna(roll_number):
            return ""
        
        cleaned = str(roll_number).strip()
        
        if not self.config['case_sensitive']:
            cleaned = cleaned.upper()
        
        # Remove common separators and whitespace
        cleaned = re.sub(r'[\s\-_]+', '', cleaned)
        
        return cleaned
    
    def _find_exact_matches(self, roll_number: str, existing_rolls: List[str]) -> List[Tuple[str, int]]:
        """Find exact matches for roll number"""
        matches = []
        
        for i, existing_roll in enumerate(existing_rolls):
            if self._clean_roll_number(existing_roll) == roll_number:
                matches.append((existing_roll, i))
        
        return matches
    
    def _find_fuzzy_matches(self, roll_number: str, existing_rolls: List[str]) -> List[Tuple[str, float, int]]:
        """Find fuzzy matches for roll number"""
        matches = []
        
        for i, existing_roll in enumerate(existing_rolls):
            cleaned_existing = self._clean_roll_number(existing_roll)
            similarity = SequenceMatcher(None, roll_number, cleaned_existing).ratio()
            matches.append((existing_roll, similarity, i))
        
        # Sort by similarity (descending)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches
    
    def get_match_statistics(self, detection_results: List) -> Dict:
        """Get statistics about matching performance"""
        if not detection_results:
            return {}
        
        total_detections = len(detection_results)
        exact_matches = 0
        fuzzy_matches = 0
        no_matches = 0
        
        for result in detection_results:
            if hasattr(result, 'similarity_score'):
                if result.similarity_score == 1.0:
                    exact_matches += 1
                elif result.similarity_score >= self.config['fuzzy_match_threshold']:
                    fuzzy_matches += 1
                else:
                    no_matches += 1
        
        return {
            'total_detections': total_detections,
            'exact_matches': exact_matches,
            'fuzzy_matches': fuzzy_matches,
            'no_matches': no_matches,
            'match_rate': (exact_matches + fuzzy_matches) / total_detections if total_detections > 0 else 0,
            'exact_match_rate': exact_matches / total_detections if total_detections > 0 else 0
        }