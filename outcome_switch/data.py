from enum import Enum
from datetime import datetime
from typing import Optional, Dict


class OutcomeType(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    OTHER = "other"

class DateType(Enum):
    CURRENT = "current"
    ORIGINAL = "original"


class Outcome:

    def __init__(self, 
            text:str, 
            outcome_type:str,
            date_type:Optional[str]=None,
            submission_date:Optional[datetime] = None,
            description:Optional[str] = "",
            time_frame:Optional[str] = "", 
        ) -> None:
        """Outcome object 
        Args:
            text (str): outcome short text
            outcome_type (OutcomeType): outcome type
            date_type (Optional[str], optional): date type (current or original). Defaults to None.
            submission_date (Optional[datetime], optional): submission date. Defaults to None.
            description (Optional[str], optional): outcome description. Defaults to "".
            time_frame (Optional[str], optional): time frame. Defaults to "".
        """
        
        self.text = text
        self.outcome_type = OutcomeType(outcome_type)
        self.date_type = DateType(date_type) if date_type else None
        self.submission_date = submission_date
        self.description = description
        self.time_frame = time_frame
    
    
    def to_json(self) -> Dict[str, str]:
        string_date= self.submission_date.strftime("%Y-%m-%d") if self.submission_date else ""
        return {
            "text": self.text,
            "outcome_type": self.outcome_type.value,
            "date_type": self.date_type.value if self.date_type else "",
            "description": self.description,
            "time_frame": self.time_frame,
            "submission_date": string_date,
        }

    def __str__(self) -> str:
        return str(self.to_json())

    def compare(self, other: "Outcome") -> str:
        """Compare two outcomes and returns True if they are the same"""
        diff = []
        if self.outcome_type != other.outcome_type:
            diff.append("type")
        if self.text.lower() != other.text.lower():
            diff.append("text")
        if self.description.lower() != other.description.lower():
            diff.append("description")
        if self.time_frame.lower() != other.time_frame.lower():
            diff.append("time_frame")
        if not diff :
            diff.append("same")
        return " ".join(diff)
    