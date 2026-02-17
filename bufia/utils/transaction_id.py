"""
Transaction ID Generator for BUFIA Payment System

Generates unique internal transaction IDs in the format: BUF-TXN-YYYY-NNNNN
where YYYY is the current year and NNNNN is a zero-padded sequential number.
"""

from django.db import transaction
from django.utils import timezone
from datetime import datetime


class TransactionIDGenerator:
    """Generate unique, sequential internal transaction IDs"""
    
    PREFIX = "BUF-TXN"
    SEQUENCE_LENGTH = 5
    
    @classmethod
    def generate(cls) -> str:
        """
        Generate a unique internal transaction ID in format BUF-TXN-YYYY-NNNNN
        
        Returns:
            str: Generated transaction ID (e.g., "BUF-TXN-2026-00045")
        
        Raises:
            Exception: If unable to generate unique ID after retries
        """
        current_year = timezone.now().year
        
        # Use database transaction to ensure atomicity
        with transaction.atomic():
            sequence_number = cls.get_next_sequence_number(current_year)
            transaction_id = cls._format_transaction_id(current_year, sequence_number)
            
        return transaction_id
    
    @classmethod
    def get_next_sequence_number(cls, year: int) -> int:
        """
        Get the next sequential number for the given year
        
        Args:
            year: The year for which to get the sequence number
            
        Returns:
            int: Next sequence number (1-based)
        """
        from bufia.models import Payment
        
        # Lock the table to prevent race conditions
        # Get the highest sequence number for this year
        year_prefix = f"{cls.PREFIX}-{year}-"
        
        payments = Payment.objects.filter(
            internal_transaction_id__startswith=year_prefix
        ).select_for_update()
        
        if not payments.exists():
            return 1
        
        # Extract sequence numbers and find the maximum
        max_sequence = 0
        for payment in payments:
            if payment.internal_transaction_id:
                try:
                    # Extract the sequence part (last 5 digits)
                    sequence_str = payment.internal_transaction_id.split('-')[-1]
                    sequence_num = int(sequence_str)
                    max_sequence = max(max_sequence, sequence_num)
                except (ValueError, IndexError):
                    continue
        
        return max_sequence + 1
    
    @classmethod
    def _format_transaction_id(cls, year: int, sequence: int) -> str:
        """
        Format the transaction ID with proper padding
        
        Args:
            year: The year
            sequence: The sequence number
            
        Returns:
            str: Formatted transaction ID
        """
        sequence_str = str(sequence).zfill(cls.SEQUENCE_LENGTH)
        return f"{cls.PREFIX}-{year}-{sequence_str}"
    
    @classmethod
    def validate_format(cls, transaction_id: str) -> bool:
        """
        Validate that a transaction ID matches the expected format
        
        Args:
            transaction_id: The transaction ID to validate
            
        Returns:
            bool: True if valid format, False otherwise
        """
        import re
        pattern = r'^BUF-TXN-\d{4}-\d{5}$'
        return bool(re.match(pattern, transaction_id))
