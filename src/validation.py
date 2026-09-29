from typing import List, Dict, Any
from pydantic import ValidationError
from src.models import MeasurementRecord

def validate_records(records: List[Dict[str, Any]]) -> List[MeasurementRecord]:
    """Validates raw dictionary records against the MeasurementRecord pydantic model."""
    valid_records = []
    errors = []

    for idx, record in enumerate(records):
        try:
            valid_record = MeasurementRecord(**record)
            valid_records.append(valid_record)
        except ValidationError as e:
            errors.append(f"Record {idx} failed validation: {e}")

    if errors:
        print(f"Validation errors found in {len(errors)} records.")
        for err in errors[:5]:
            print(err)
        if len(errors) > 5:
            print(f"... and {len(errors) - 5} more errors.")
            
    return valid_records
