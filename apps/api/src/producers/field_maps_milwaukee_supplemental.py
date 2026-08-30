"""Field maps for Milwaukee's viable US-220 CKAN supplementation candidates."""

from typing import Dict, List

from src.spatial.cities.milwaukee import MILWAUKEE_SUPPLEMENTAL_FEED_SPECS


FIELD_MAP: Dict[str, Dict[str, List[str]]] = {
    "fire_calls": {
        "event_id": ["IncidentNumber"],
        "created_date": ["IncidentStarted"],
        "latitude": ["latitude"],
        "longitude": ["longitude"],
        "address": ["Location"],
        "category": ["IncidentType"],
    },
    "ems_calls": {
        "event_id": ["_id"],
        "created_date": ["IncidentAdded"],
        "category": ["typ_eng"],
        "subcategory": ["sub_eng"],
        "district": ["AldDist"],
        "zipcode": ["zip"],
    },
    "vacant_buildings": {
        "event_id": ["PARCELNBR", "_id"],
        "created_date": ["DATEOPENED"],
        "address": ["ADDRFULLLINE"],
        "category": ["LANDUSE"],
        "value": ["VALUEIMPROVED"],
        "district": ["AldermanicDistrict"],
        "zipcode": ["ZipCode"],
        "neighborhood": ["Neighborhood"],
    },
    "liquor_licenses": {
        "event_id": ["TAXKEY", "TAXKEY_NUMBER"],
        "effective_date": ["EFF_DATE"],
        "expiration_date": ["EXP_DATE"],
        "license_type": ["LIC_TYPE", "License Type Full Name"],
        "premises_name": ["CORP_NAME"],
        "dba": ["TRADE_NAME"],
        "address": ["HOUSE_NR", "STREET", "STTYPE"],
        "district": ["POLICE_DISTRICT", "ALDERMANIC_DISTRICT"],
    },
    "delinquent_tax_accounts": {
        "event_id": ["Tax Key #"],
        "period": ["Levy Year"],
        "address": ["Property Address"],
        "district": ["Ald Dist"],
        "owner": ["Owner's Name"],
        "amount": ["Total Tax Principal"],
        "zipcode": ["Zip"],
    },
}


assert set(FIELD_MAP) == set(MILWAUKEE_SUPPLEMENTAL_FEED_SPECS)
