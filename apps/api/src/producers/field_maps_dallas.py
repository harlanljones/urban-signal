"""Dallas, TX field maps for the ROW and partial 311 feeds."""

from typing import Dict, List

# canonical event field -> ordered candidate row keys (dotted = nested container)
ROW_FIELD_MAP: Dict[str, List[str]] = {
    "job_id": ["EXTERNALFILENUM", "JOBID", "OBJECTID"],
    "job_type": ["PERMITTYPE", "ROWREASONFORJOB", "ROWIMPROVEMENTREPAIR"],
    "issuance_date": ["ISSUEDATE"],
    "filing_date": ["CREATEDDATE"],
    "status": ["STATUSDESCRIPTION"],
    "borough": ["COUNCIL_DISTRICTS"],
    "address_street": ["LOCATIONNAMES", "SPECIFICLOCATION"],
}

# Preserve the descriptive names used by the Dallas permit module and tests.
DALLAS_FIELD_MAP = ROW_FIELD_MAP
FIELD_MAP = ROW_FIELD_MAP


DALLAS_311_FIELD_MAP: Dict[str, List[str]] = {
    "incident_id": ["Service_Request_Number_c", "CaseNumber", "OBJECTID"],
    "created_date": ["CreatedDate"],
    "closed_date": ["ClosedDate"],
    "status": ["Status"],
    "complaint_type": ["Subject", "Service_Type_Version_Code_c"],
    "incident_address": ["Address_c", "Location_Details_c"],
    "borough": ["Council_District_c", "City_Service_Area_c"],
    "zipcode": ["Zipcode_c"],
    "latitude": ["Location_Latitude_s"],
    "longitude": ["Location_Longitude_s"],
}
