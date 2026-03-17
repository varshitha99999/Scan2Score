"""
Validation Engine for Roll Number Detection
==========================================
Validates detected roll numbers against expected formats and business rules.
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class ValidationResult:
    """Result of roll number validation"""
    is_valid: bool
    corrected_roll_number: Optional[str]
    validation_score: float
    error_messages: List[str]
    suggestions: List[str]


class ValidationEngine:
    """
    Validates detected roll numbers against expected formats and patterns.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize validation engine with configuration.
        
        Args:
            config: Configuration dictionary with validation rules
        """
        self.config = config or self._default_config()
        self.format_patterns = [re.compile(pattern) for pattern in self.config['format_patterns']]
    
    def _default_config(self) -> Dict:
        """Default validation configuration"""
        return {
            'format_patterns': [
                r'^\d{2}[A-Z]{2}\d[A-Z]\d{4}$',  # 23WH1A1253 format
                r'^\d{4}[A-Z]{2}\d{3}$',         # 2023CS001 format
                r'^\d{2}[A-Z]{2}\d[A-Z]\d{3}$',  # 23WH1A123 format
            ],
            'min_confidence': 0.7,
            'fuzzy_match_threshold': 0.8,
            'max_length': 15,
            'min_length': 6,
            'allowed_chars': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
            'common_corrections': {
                '0': ['O', 'D'],
                'O': ['0'],
                '1': ['I', 'l'],
                'I': ['1'],
                '5': ['S'],
                'S': ['5'],
                '8': ['B'],
                'B': ['8'],
                '6': ['G'],
                'G': ['6']
            }
        }
    
    def validate_roll_number(self, roll_number: str, confidence: float) -> ValidationResult:
        """
        Validate a detected roll number.
        
        Args:
            roll_number: The detected roll number string
            confidence: Detection confidence score (0.0 to 1.0)
            
        Returns:
            ValidationResult with validation status and suggestions
        """
        error_messages = []
        suggestions = []
        corrected_roll_number = None
        
        # Basic checks
        if not roll_number or roll_number in ['NOT_FOUND', 'ERROR']:
            return ValidationResult(
                is_valid=False,
                corrected_roll_number=None,
                validation_score=0.0,
                error_messages=['Roll number not detected'],
                suggestions=['Check image quality and blue ink visibility']
            )
        
        # Clean the roll number
        cleaned_roll = self._clean_roll_number(roll_number)
        
        # Length validation
        if len(cleaned_roll) < self.config['min_length']:
            error_messages.append(f'Roll number too short (minimum {self.config["min_length"]} characters)')
        elif len(cleaned_roll) > self.config['max_length']:
            error_messages.append(f'Roll number too long (maximum {self.config["max_length"]} characters)')
        
        # Character validation
        invalid_chars = [c for c in cleaned_roll if c not in self.config['allowed_chars']]
        if invalid_chars:
            error_messages.append(f'Invalid characters found: {", ".join(set(invalid_chars))}')
        
        # Confidence validation
        if confidence < self.config['min_confidence']:
            error_messages.append(f'Low detection confidence: {confidence:.2f} (minimum {self.config["min_confidence"]})')
        
        # Format validation
        format_match = self._check_format_compliance(cleaned_roll)
        if not format_match:
            error_messages.append('Roll number format does not match expected patterns')
            # Try to suggest corrections
            corrected_roll = self._suggest_format_correction(cleaned_roll)
            if corrected_roll:
                suggestions.append(f'Suggested correction: {corrected_roll}')
                corrected_roll_number = corrected_roll
        
        # Calculate validation score
        validation_score = self._calculate_validation_score(cleaned_roll, confidence, format_match)
        
        # Determine if valid
        is_valid = (
            len(error_messages) == 0 or 
            (validation_score >= 0.8 and confidence >= self.config['min_confidence'])
        )
        
        return ValidationResult(
            is_valid=is_valid,
            corrected_roll_number=corrected_roll_number or cleaned_roll,
            validation_score=validation_score,
            error_messages=error_messages,
            suggestions=suggestions
        )
    
    def check_format_compliance(self, roll_number: str) -> bool:
        """Check if roll number matches expected format patterns"""
        cleaned_roll = self._clean_roll_number(roll_number)
        return self._check_format_compliance(cleaned_roll)
    
    def detect_duplicates(self, roll_numbers: List[str]) -> List[str]:
        """Identify duplicate roll numbers in a batch"""
        seen = set()
        duplicates = []
        
        for roll in roll_numbers:
            cleaned = self._clean_roll_number(roll)
            if cleaned in seen and cleaned not in duplicates:
                duplicates.append(cleaned)
            seen.add(cleaned)
        
        return duplicates
    
    def suggest_corrections(self, roll_number: str) -> List[str]:
        """Suggest possible corrections for an invalid roll number"""
        suggestions = []
        cleaned_roll = self._clean_roll_number(roll_number)
        
        # Try common character corrections
        corrected = self._apply_common_corrections(cleaned_roll)
        if corrected != cleaned_roll and self._check_format_compliance(corrected):
            suggestions.append(corrected)
        
        # Try format-based corrections
        format_corrected = self._suggest_format_correction(cleaned_roll)
        if format_corrected and format_corrected not in suggestions:
            suggestions.append(format_corrected)
        
        return suggestions
    
    def _clean_roll_number(self, roll_number: str) -> str:
        """Clean and normalize roll number string"""
        if not roll_number:
            return ""
        
        # Remove whitespace and convert to uppercase
        cleaned = roll_number.strip().upper()
        
        # Remove common OCR artifacts
        cleaned = cleaned.replace(' ', '').replace('-', '').replace('_', '')
        
        return cleaned
    
    def _check_format_compliance(self, roll_number: str) -> bool:
        """Check if roll number matches any of the expected patterns"""
        for pattern in self.format_patterns:
            if pattern.match(roll_number):
                return True
        return False
    
    def _calculate_validation_score(self, roll_number: str, confidence: float, format_match: bool) -> float:
        """Calculate overall validation score"""
        score = 0.0
        
        # Confidence contributes 40%
        score += confidence * 0.4
        
        # Format match contributes 30%
        if format_match:
            score += 0.3
        
        # Length appropriateness contributes 20%
        if self.config['min_length'] <= len(roll_number) <= self.config['max_length']:
            score += 0.2
        
        # Character validity contributes 10%
        valid_chars = sum(1 for c in roll_number if c in self.config['allowed_chars'])
        if len(roll_number) > 0:
            score += (valid_chars / len(roll_number)) * 0.1
        
        return min(score, 1.0)
    
    def _suggest_format_correction(self, roll_number: str) -> Optional[str]:
        """Suggest format-based correction for roll number"""
        # Try to match against expected patterns and suggest corrections
        
        # For 23WH1A1253 format (most common)
        if len(roll_number) >= 8:
            # Try to extract components
            digits_start = ''.join(c for c in roll_number[:2] if c.isdigit())
            letters_mid = ''.join(c for c in roll_number[2:4] if c.isalpha())
            digit_mid = ''.join(c for c in roll_number[4:5] if c.isdigit())
            letter_mid = ''.join(c for c in roll_number[5:6] if c.isalpha())
            digits_end = ''.join(c for c in roll_number[6:] if c.isdigit())
            
            if len(digits_start) >= 2 and len(letters_mid) >= 2 and digit_mid and letter_mid:
                suggested = f"{digits_start[:2]}{letters_mid[:2]}{digit_mid}{letter_mid}{digits_end[:4].zfill(4)}"
                if self._check_format_compliance(suggested):
                    return suggested
        
        return None
    
    def _apply_common_corrections(self, roll_number: str) -> str:
        """Apply common OCR error corrections"""
        corrected = roll_number
        
        for correct_char, wrong_chars in self.config['common_corrections'].items():
            for wrong_char in wrong_chars:
                corrected = corrected.replace(wrong_char, correct_char)
        
        return corrected
    
    def fuzzy_match_roll_numbers(self, roll_number: str, candidates: List[str]) -> List[Tuple[str, float]]:
        """Find similar roll numbers using fuzzy matching"""
        matches = []
        cleaned_roll = self._clean_roll_number(roll_number)
        
        for candidate in candidates:
            cleaned_candidate = self._clean_roll_number(candidate)
            similarity = SequenceMatcher(None, cleaned_roll, cleaned_candidate).ratio()
            
            if similarity >= self.config['fuzzy_match_threshold']:
                matches.append((candidate, similarity))
        
        # Sort by similarity score (descending)
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches
    
    def get_validation_stats(self, results: List[ValidationResult]) -> Dict:
        """Get validation statistics for a batch of results"""
        if not results:
            return {}
        
        valid_count = sum(1 for r in results if r.is_valid)
        avg_score = sum(r.validation_score for r in results) / len(results)
        
        error_types = {}
        for result in results:
            for error in result.error_messages:
                error_types[error] = error_types.get(error, 0) + 1
        
        return {
            'total_processed': len(results),
            'valid_count': valid_count,
            'invalid_count': len(results) - valid_count,
            'success_rate': valid_count / len(results),
            'average_validation_score': avg_score,
            'common_errors': error_types
        }