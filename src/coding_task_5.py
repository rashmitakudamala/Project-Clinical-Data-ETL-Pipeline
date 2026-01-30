import json
from datetime import datetime
from pathlib import Path
import requests
from hl7apy.core import Message
from src.registration import data_dir

BASE_URL = "https://in-info-web20.luddy.indianapolis.iu.edu/apis/default/fhir"  # OpenEMR FHIR server
BASE_HERMES_URL = 'http://159.203.121.13:8080/v1/snomed'  # Hermes terminology server
PRIMARY_FHIR_URL = 'http://159.203.105.138:8080/fhir'  # Primary care EHR FHIR server

# Fixed OpenEMR Patient id used across tasks
patient_resource_id = "9d036484-c661-485c-899d-fcab43d40914"


def get_access_token_from_file():
    """
        Read the OAuth access token from data/access_token.json.
        Returns the access_token string, or None if the file is missing/invalid.
    """
    file_path = Path(data_dir / "access_token.json")
    if not file_path.exists():
        print("Error: access_token.json file not found.")
        return None
    try:
        with open(file_path, 'r') as json_file:
            json_data = json.load(json_file)
            access_token = json_data.get("access_token")
        return access_token
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error reading access token from file: {e}")
        return None


def get_headers():
    """
        Helper to build the Authorization headers for FHIR requests
        using the access token read from file.
    """
    access_token = get_access_token_from_file()
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    return headers


def get_fhir_patient(patient_resource_id: str) -> dict:
    """
        Fetch the Patient resource for the given OpenEMR patient id.
        Returns dict: Parsed Patient JSON from the FHIR server.
    """
    url = f'{BASE_URL}/Patient/{patient_resource_id}'
    response = requests.get(url=url, headers=get_headers())
    print("Patient URL:", response.url)
    data = response.json()
    print("Patient from OpenEMR:")
    print(json.dumps(data, indent=2))
    return data


def load_condition_json() -> dict:
    """
        Load the parent_condition.json file that was created in Task 1
        Returns dict: Parsed Condition JSON.
    """
    with open(data_dir / "parent_condition.json") as f:
        condition_data = json.load(f)
    return condition_data


def map_snomed_to_icd10(snomed_code: str, snomed_term: str):
    """
       Use the Hermes terminology server to map a SNOMED CT code to an ICD-10-CM code using the WHO map refset 447562003.
       Returns (icd10_code, icd10_term)
   """
    url = f"{BASE_HERMES_URL}/concepts/{snomed_code}/map/447562003"
    response = requests.get(url=url)
    try:
        data = response.json()
        print("Response JSON:", data)
    except ValueError:
        print("No results found")
        print(response.text)
        return None, None
    if not data:
        print(f"No ICD-10 mapping found for SNOMED {snomed_code}")
        return None, None

    mapping = data[0]
    icd10_code = mapping.get("mapTarget")
    icd10_term = snomed_term

    print(f'{icd10_code} is the mapped ICD-10 code for SNOMED {snomed_code} - {snomed_term}')
    return icd10_code, icd10_term


def create_adt_message(patient_data: dict, condition_data: dict, icd10_code: str, icd10_term: str) -> None:
    """
        Construct an HL7 v2 ADT^A01 message using:
          - Patient data from OpenEMR FHIR Patient resource
          - Condition data (SNOMED condition) from parent_condition.json
          - ICD-10 code mapped from Hermes terminology server

        Segments included:
          - MSH: message header
          - PID: patient identification
          - PV1: patient visit (outpatient)
          - DG1: diagnosis (ICD-10 + SNOMED term)
    """
    # Basic patient demographics
    patient_id = patient_data.get("id", "")

    name = patient_data.get("name")[0]
    family = name.get("family", "")
    given_list = name.get("given", [""])
    given = given_list[0] if given_list else ""
    full_name = f"{family}^{given}"

    gender = patient_data.get("gender", "").upper()[0]  # M or F
    birthdate_raw = patient_data.get("birthDate", "")
    birthdate = birthdate_raw.replace("-", "")

    address = patient_data.get("address")[0]
    line = address.get("line")[0]
    city = address.get("city", "")
    state = address.get("state", "")
    postal = address.get("postalCode", "")

    # SNOMED concept condition description
    code = condition_data["code"]["coding"][0]
    snomed_code = code["code"]
    snomed_term = code["display"]

    # HL7 message
    msg = Message("ADT_A01")

    # MSH segment
    now_ts = datetime.now().strftime("%Y%m%d%H%M%S")

    msg.msh.msh_3 = "MyApp"  # sending application
    msg.msh.msh_4 = "OpenEMR"  # sending facility
    msg.msh.msh_5 = "PrimaryCareEHR"  # receiving application
    msg.msh.msh_6 = "PrimaryFacility"  # receiving facility
    msg.msh.msh_7 = now_ts  # message timestamp
    msg.msh.msh_9 = "ADT^A01"  # message type
    msg.msh.msh_10 = "MSG00001"  # msg control id
    msg.msh.msh_11 = "P"  # Processing ID
    msg.msh.msh_12 = "2.5"  # version

    # PID segment
    msg.pid.pid_1 = "1"
    msg.pid.pid_3 = patient_id  # patient id
    msg.pid.pid_5 = full_name  # Family^Given
    msg.pid.pid_7 = birthdate  # YYYYMMDD
    msg.pid.pid_8 = gender  # M/F
    msg.pid.pid_11 = f"{line}^{city}^{state}^{postal}^^H"  # PID-11 - address: street^city^state^zip^^H

    # PV1 segment (patient visit)
    msg.pv1.pv1_1 = "1"
    msg.pv1.pv1_2 = "O"  # O = outpatient

    # DG1 segment (Diagnosis segment)
    msg.dg1.dg1_1 = "1"
    msg.dg1.dg1_3 = f"{icd10_code}^{icd10_term}^I10"  # DG1-3: ICD code^ICD description^coding system
    msg.dg1.dg1_4 = snomed_term  # DG1-4: Diagnosis description

    # Save message to .txt file in ER7 format
    out_path = data_dir / "adt_message.txt"
    with open(out_path, "w") as f:
        f.write(msg.to_er7())

    print("HL7 ADT^A01 message created and saved to:", out_path)
    print()
    print("ADT Message:")
    print(msg.to_er7().replace('\r', '\n'))


if __name__ == '__main__':
    print()
    # 1. Fetch patient data from OpenEMR FHIR Patient resource
    patient_data = get_fhir_patient(patient_resource_id)
    # 2. Load Condition (parent_condition.json) created in Task 1
    condition_data = load_condition_json()
    # 3. Extract SNOMED code/term and map to ICD-10 using Hermes
    snomed_code = condition_data["code"]["coding"][0]["code"]
    snomed_term = condition_data["code"]["coding"][0]["display"]
    icd10_code, icd10_term = map_snomed_to_icd10(snomed_code, snomed_term)
    # 4. Construct HL7 message
    create_adt_message(patient_data, condition_data, icd10_code, icd10_term)
