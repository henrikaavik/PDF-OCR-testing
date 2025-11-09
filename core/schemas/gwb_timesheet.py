"""
Pydantic schema for GWB Monthly Time Sheet structure.
Ensures 100% field extraction with OpenAI Structured Outputs.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class ServiceProviderDetails(BaseModel):
    """SERVICE PROVIDER DETAILS section (blue header)."""
    service_provider: str = Field(description="Service Provider name (SURNAME, Name)")
    service_provider_start_date: str = Field(description="Start date (dd/mm/yyyy)")
    type: str = Field(description="Type (e.g., QTM, GTM)")
    profile: str = Field(description="Profile/role (e.g., Junior Allowance Specialist)")
    place_of_delivery: str = Field(description="Place of delivery/location")


class ContractInformation(BaseModel):
    """CONTRACT INFORMATION section (blue header)."""
    specific_contract_number: str = Field(description="Specific Contract Number")
    specific_contract_start_date: str = Field(description="Contract start date (dd/mm/yyyy)")
    specific_contract_end_date: str = Field(description="Contract end date (dd/mm/yyyy)")
    lot_no: str = Field(description="Lot number")
    contractor_name: str = Field(description="Contractor name/company")
    framework_contract_number: str = Field(description="Framework Contract Number")
    program: str = Field(description="Program name")


class TimesheetDetails(BaseModel):
    """TIMESHEET DETAILS section (blue header)."""
    service_request_number: str = Field(description="Service Request Number (e.g., SR2)")
    service_request_start_date: str = Field(description="Service Request start date (dd/mm/yyyy)")
    service_request_end_date: str = Field(description="Service Request end date (dd/mm/yyyy)")


class SummaryTableRow(BaseModel):
    """Row in the summary table (Effort for Normal Working Hours)."""
    service_request: str = Field(description="Service Request identifier")
    contractual_days_onsite: Optional[str] = Field(default=None, description="Contractual Days Onsite")
    contractual_days_offsite: Optional[str] = Field(default=None, description="Contractual Days Offsite")
    available_days_onsite: Optional[str] = Field(default=None, description="Available Days Onsite")
    available_days_offsite: Optional[str] = Field(default=None, description="Available Days Offsite")
    consumed_days_onsite: Optional[str] = Field(default=None, description="Consumed Days Onsite")
    consumed_days_offsite: Optional[str] = Field(default=None, description="Consumed Days Offsite")
    remaining_days_onsite: Optional[str] = Field(default=None, description="Remaining Days Onsite")
    remaining_days_offsite: Optional[str] = Field(default=None, description="Remaining Days Offsite")


class SummaryTable(BaseModel):
    """Effort for Normal Working Hours summary table."""
    section_title: str = Field(default="Effort for Normal Working Hours (h)", description="Table section title")
    rows: List[SummaryTableRow] = Field(description="All rows including totals")


class DailyCalendarRow(BaseModel):
    """Row in the daily calendar table (days 1-31)."""
    service_request: str = Field(description="Service Request identifier")
    day_1: Optional[str] = Field(default=None, description="Hours for day 1")
    day_2: Optional[str] = Field(default=None, description="Hours for day 2")
    day_3: Optional[str] = Field(default=None, description="Hours for day 3")
    day_4: Optional[str] = Field(default=None, description="Hours for day 4")
    day_5: Optional[str] = Field(default=None, description="Hours for day 5")
    day_6: Optional[str] = Field(default=None, description="Hours for day 6")
    day_7: Optional[str] = Field(default=None, description="Hours for day 7")
    day_8: Optional[str] = Field(default=None, description="Hours for day 8")
    day_9: Optional[str] = Field(default=None, description="Hours for day 9")
    day_10: Optional[str] = Field(default=None, description="Hours for day 10")
    day_11: Optional[str] = Field(default=None, description="Hours for day 11")
    day_12: Optional[str] = Field(default=None, description="Hours for day 12")
    day_13: Optional[str] = Field(default=None, description="Hours for day 13")
    day_14: Optional[str] = Field(default=None, description="Hours for day 14")
    day_15: Optional[str] = Field(default=None, description="Hours for day 15")
    day_16: Optional[str] = Field(default=None, description="Hours for day 16")
    day_17: Optional[str] = Field(default=None, description="Hours for day 17")
    day_18: Optional[str] = Field(default=None, description="Hours for day 18")
    day_19: Optional[str] = Field(default=None, description="Hours for day 19")
    day_20: Optional[str] = Field(default=None, description="Hours for day 20")
    day_21: Optional[str] = Field(default=None, description="Hours for day 21")
    day_22: Optional[str] = Field(default=None, description="Hours for day 22")
    day_23: Optional[str] = Field(default=None, description="Hours for day 23")
    day_24: Optional[str] = Field(default=None, description="Hours for day 24")
    day_25: Optional[str] = Field(default=None, description="Hours for day 25")
    day_26: Optional[str] = Field(default=None, description="Hours for day 26")
    day_27: Optional[str] = Field(default=None, description="Hours for day 27")
    day_28: Optional[str] = Field(default=None, description="Hours for day 28")
    day_29: Optional[str] = Field(default=None, description="Hours for day 29")
    day_30: Optional[str] = Field(default=None, description="Hours for day 30")
    day_31: Optional[str] = Field(default=None, description="Hours for day 31")


class DailyCalendar(BaseModel):
    """Daily hours calendar table (days 1-31)."""
    section_title: Optional[str] = Field(default=None, description="Table section title if present")
    rows: List[DailyCalendarRow] = Field(description="Daily hours for each service request")


class GWBTimesheet(BaseModel):
    """
    Complete GWB Monthly Time Sheet structure.

    This schema ensures ALL sections are extracted:
    - Service Provider Details (5 fields)
    - Contract Information (7 fields)
    - Timesheet Details (3 fields)
    - Summary Table (effort hours)
    - Daily Calendar (days 1-31)

    Used with OpenAI Structured Outputs for 100% schema adherence.
    """
    service_provider_details: ServiceProviderDetails = Field(description="SERVICE PROVIDER DETAILS section")
    contract_information: ContractInformation = Field(description="CONTRACT INFORMATION section")
    timesheet_details: TimesheetDetails = Field(description="TIMESHEET DETAILS section")
    summary_table: SummaryTable = Field(description="Effort for Normal Working Hours table")
    daily_calendar: DailyCalendar = Field(description="Daily hours calendar (1-31 days)")
