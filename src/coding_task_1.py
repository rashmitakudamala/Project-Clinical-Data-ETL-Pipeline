import json
import requests
from pprint import pprint
from pathlib import Path
from src.registration import data_dir

BASE_URL = "https://in-info-web20.luddy.indianapolis.iu.edu/apis/default/fhir" # OpenEMR FHIR server
BASE_HERMES_URL = 'http://159.203.121.13:8080/v1/snomed' # Hermes terminology server
PRIMARY_FHIR_URL = 'http://159.203.105.138:8080/fhir' # Primary care EHR FHIR server

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


def get_fhir_resource(resource_name):
    """
        Generic helper to GET any FHIR resource collection
        from the OpenEMR FHIR server.
    """
    url = f'{BASE_URL}/{resource_name}'
    response = requests.get(url=url, headers=get_headers())
    print(response.url)
    pprint(response.json())


def get_fhir_patient(resource_id):
    """
        Fetch and print a specific Patient resource
        from the OpenEMR FHIR server by its id.
    """
    url = f'{BASE_URL}/Patient/{resource_id}'
    response = requests.get(url=url, headers=get_headers())
    print(response.url)
    pprint(response.json())


def get_patient_gender_where_dob_greater_than(name, gender, birth_date):
    """
        Demonstrates a filtered FHIR search:
        GET /Patient?name={name}&gender={gender}&birthdate=gt{birth_date}
        Prints each matching patient's id, gender, birthDate and full name.
    """
    url = f'{BASE_URL}/Patient?name={name}&gender={gender}&birthdate=gt{birth_date}'
    response = requests.get(url=url, headers=get_headers())
    print(response.url)
    data = response.json()
    if 'entry' in data:
        print(f"Number of entries: {len(data['entry'])}")
        entry = data['entry']
        for item in entry:
            resource_id = item['resource']['id']
            given_name = f"{item['resource']['name'][0]['given'][0]}"
            family_name = f"{item['resource']['name'][0]['family']}"
            print(f"{resource_id} - {item['resource']['gender']} - {item['resource']['birthDate']} - {given_name} {family_name}")
    else:
        print('No results found')

def search_condition(patient_resource_id):
    """
        List all Condition resources in OpenEMR for a given patient.
        Prints resourceType, id, and SNOMED code for each Condition.
    """
    url = f'{BASE_URL}/Condition?patient={patient_resource_id}'
    response = requests.get(url=url, headers=get_headers())
    print(response.url)
    data = response.json()
    if 'entry' in data:
        print(f"Number of entries: {len(data['entry'])}")
        print()
        entry = data.get('entry')
        for item in entry:
            resource_type = item['resource']['resourceType']
            resource_id = item['resource']['id']
            code = item['resource']['code']['coding'][0]['code']
            display = item['resource']['code']['coding'][0]['display']
            print(f'Resource type: {resource_type}')
            print(f'Resource ID: {resource_id}')
            print(f'Code: {code}')
            print()

    else:
        print('No results found')


def get_one_condition(patient_resource_id):
    """
       Get the first Condition resource for a given patient from OpenEMR
       and print its type, id, SNOMED code.
   """
    url = f'{BASE_URL}/Condition?patient={patient_resource_id}'
    response = requests.get(url=url, headers=get_headers())
    print(response.url)
    data = response.json()

    if 'entry' in data:
        entry = data['entry'][0]
        resource_type = entry['resource']['resourceType']
        resource_id = entry['resource']['id']
        code = entry['resource']['code']['coding'][0]['code']
        display = entry['resource']['code']['coding'][0]['display']
        print()
        print("Selected condition for patient resource:")
        print(f'Resource type: {resource_type}')
        print(f'Resource ID: {resource_id}')
        print(f'Code: {code}')
        print()
    else:
        print('No results found')

def get_parent_for_code(patient_resource_id):
    """
        Retrieve the first Condition for the patient from OpenEMR,
        extract its SNOMED code, and query Hermes for the parent concept.
        Returns (parent_id, parent_term) if found, or None if no parent could be found.
    """
    url = f'{BASE_URL}/Condition?patient={patient_resource_id}'
    response = requests.get(url=url, headers=get_headers())
    print(response.url)
    data = response.json()
    if 'entry' not in data or not data['entry']:
        print('No Condition resources found for this patient')
        return None, None
    if 'entry' in data:
        entry = data['entry'][0]
        resource_type = entry['resource']['resourceType']
        resource_id = entry['resource']['id']
        code = entry['resource']['code']['coding'][0]['code']
        display = entry['resource']['code']['coding'][0]['display']

    # Use Hermes terminology server to get the parent SNOMED concept
    snomed_url = f'{BASE_HERMES_URL}/search?constraint=>!{code}'
    response = requests.get(url=snomed_url)
    print(response.url)
    if response.status_code != 200:
        print(f"Hermes error: {response.status_code}")
        return None, None
    data = response.json()
    if data:
        parent_id = data[0].get('conceptId')
        parent_term = data[0].get('preferredTerm')
        print(f"Parent concept for selected condition: {code}")
        print(f'Parent concept ID: {parent_id}')
        print(f'Parent preferred term: {parent_term}')
        print()
        return parent_id, parent_term
    else:
        print('No results found')
        return None

PATIENT_PROFILE_URL = "http://example.org/StructureDefinition/my-patient-profile"
def create_patient_resource(patient_resource_id):
    """
    Fetch Patient from OpenEMR, remove ids/SSN/extension, fix address text/district,
    and POST a new Patient to the Primary Care EHR.
    Returns created_patient(): The Patient resource as created on PRIMARY_FHIR_URL.
    """
    url = f'{BASE_URL}/Patient/{patient_resource_id}'
    response = requests.get(url=url, headers=get_headers())
    print(response.url)
    data = response.json()
    print()
    print("Source Patient from OpenEMR:")
    # pprint(data)
    print()

    # Removing id and meta for the server to add one
    data.pop('id', None)
    data.pop('meta', None)
    data.pop("extension", None)

    # remove SSN identifier if present
    identifiers = data.get("identifier", [])
    for i, ident in enumerate(list(identifiers)):
        if "us-ssn" in ident.get("system", ""):
            identifiers.pop(i)
            break
    data["identifier"] = identifiers

    # fix address - district
    if "address" in data and data["address"]:
        address = data["address"][0]

        # set district to "Not found" if missing/blank
        if "district" not in address or not address["district"]:
            address["district"] = "Not found"

        line = (address.get("line") or [""])[0]
        city = address.get("city", "")
        district = address.get("district", "")
        state = address.get("state", "")
        postal = address.get("postalCode", "")

        address["text"] = f"{line} {city}, {district}, {state} {postal}".strip()

    #POST
    fhir_url = f'{PRIMARY_FHIR_URL}/Patient'
    headers = {'Content-Type': 'application/fhir+json'}
    print(f'POST {fhir_url}')
    create_response = requests.post(url=fhir_url, headers=headers, json=data)
    print(create_response.url)

    created_patient = create_response.json()
    print()
    print("Created Patient resource on primary care EHR:")
    print(created_patient)
    print()

    return created_patient

CONDITION_PROFILE_URL = "http://example.org/StructureDefinition/my-condition-profile"
def create_condition_resource(primary_patient_id, parent_id, parent_term):
    """
    Build a Condition resource using the SNOMED parent concept and
    create it on the Primary Care EHR linked to the primary_patient_id.
    Adds clinicalStatus, verificationStatus, category, severity, bodySite, and onsetDateTime.
    """
    condition_resource = {
        "resourceType": "Condition",
        "text": {
            "status": "generated",
            "div": (
                '<div xmlns="http://www.w3.org/1999/xhtml">'
                f"<p>{parent_term}</p>"
                "</div>"
            )
        },
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active",
                    'display': 'Active'
                }
            ]
        },
        "verificationStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "confirmed",
                    "display": "Confirmed"
                }
            ]
        },
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-category",
                        "code": "encounter-diagnosis",
                        "display": "Encounter Diagnosis"
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": parent_id,
                    "display": parent_term
                }
            ],
            "text": parent_term
        },
        "severity": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "24484000",
                    "display": "Severe"
                }
            ],
            "text": "Severe"
        },
        "bodySite": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "34508005",
                        "display": "Structure of mucous membrane of nose"
                    }
                ],
                "text": "Mucous membrane of nose"
            }
        ],
        "onsetDateTime": "2012-05-24",
        "subject": {
            "reference": f"Patient/{primary_patient_id}"
        }
    }
    # POST
    fhir_url = f'{PRIMARY_FHIR_URL}/Condition'
    headers = {'Content-Type': 'application/fhir+json'}
    print(f'POST {fhir_url}')
    response = requests.post(url=fhir_url, headers=headers, json=condition_resource)
    print(response.url)

    created_condition = response.json()
    print()
    print("Created Condition resource on primary care EHR:")
    resource_type = created_condition.get('resourceType')
    resource_id = created_condition.get('id')
    code = created_condition['code']['coding'][0]['code']
    display = created_condition['code']['coding'][0]['display']
    print(f'Resource type: {resource_type}')
    print(f'Resource ID: {resource_id}')
    print(f'Code: {code}')
    print(f'Display: {display}')
    print()
    return created_condition

def create_patient_json_for_validation(primary_patient_id):
    """
        Reads the Patient from the Primary Care EHR, attaches the profile URL, removes SSN identifier,
        fixes address.text/district, and saves it to patient.json for validation.
    """
    url = f'{PRIMARY_FHIR_URL}/Patient/{primary_patient_id}'
    response = requests.get(url=url)
    print(url)
    data = response.json()

    # Add profile URL into meta.profile
    meta = data.get("meta", {})
    meta["profile"] = [PATIENT_PROFILE_URL]
    data["meta"] = meta

    # Remove extension
    data.pop("extension", None)

    # Remove SSN identifier if present
    identifiers = data.get("identifier", [])
    for i, ident in enumerate(list(identifiers)):
        if "us-ssn" in ident.get("system", ""):
            identifiers.pop(i)
            break
    data["identifier"] = identifiers

    # Ensure address text and district are set correctly
    if "address" in data and data["address"]:
        address = data["address"][0]
        # district, if missing
        if "district" not in address:
            address["district"] = "Not found"

        line = (address.get("line") or [""])[0]
        city = address.get("city", "")
        district = address.get("district", "")
        state = address.get("state", "")
        postal = address.get("postalCode", "")

        address["text"] = f"{line} {city}, {district}, {state} {postal}".strip()

        # Save final JSON for validation
        with open(data_dir / "patient.json", "w") as f:
            json.dump(data, f, indent=2)

        print("Created patient.json for validation")
        print()

def create_condition_json_for_validation(primary_condition_id):
    """
        Reads the Condition from the Primary Care EHR, attaches the profile URL,
        normalizes category, and saves it to parent_condition.json for validation.
    """
    url = f'{PRIMARY_FHIR_URL}/Condition/{primary_condition_id}'
    response = requests.get(url=url)
    print(url)
    data = response.json()

    # Attach profile for Condition
    meta = data.get("meta", {})
    meta["profile"] = [CONDITION_PROFILE_URL]
    data["meta"] = meta

    # Ensure clinicalStatus exists
    if "clinicalStatus" not in data:
        data["clinicalStatus"] = {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active"
                }
            ]
        }

    # Normalize the category to "encounter-diagnosis"
    category_coding = {
        "system": "http://terminology.hl7.org/CodeSystem/condition-category",
        "code": "encounter-diagnosis",
        "display": "Encounter Diagnosis"
    }

    if "category" in data and data["category"]:
        # overwrite first category coding to match example
        data["category"][0]["coding"] = [category_coding]
    else:
        data["category"] = [
            {
                "coding": [category_coding]
            }
        ]
    with open(data_dir / "parent_condition.json", "w") as f:
        json.dump(data, f, indent=2)

    print("Created parent_condition.json for validation")
    print()


if __name__ == '__main__':
    print()
    # 1. Demonstrate filtered patient search on OpenEMR
    get_patient_gender_where_dob_greater_than(name = 'James', gender = 'male', birth_date='2000-01-01')
    # 2. Inspect patient and condition from OpenEMR
    get_fhir_patient(resource_id='9d036484-c661-485c-899d-fcab43d40914')
    search_condition(patient_resource_id='9d036484-c661-485c-899d-fcab43d40914')
    get_one_condition(patient_resource_id='9d036484-c661-485c-899d-fcab43d40914')
    # 3. Get parent SNOMED concept from Hermes
    get_parent_for_code(patient_resource_id='9d036484-c661-485c-899d-fcab43d40914')
    # 4. Create Patient resource on Primary Care EHR
    patient_resource = create_patient_resource(patient_resource_id='9d036484-c661-485c-899d-fcab43d40914')
    primary_patient_id = patient_resource.get('id')
    with open(data_dir / "primary_patient_id.txt", "w") as f:
        f.write(str(primary_patient_id))
    parent_id, parent_term = get_parent_for_code(patient_resource_id='9d036484-c661-485c-899d-fcab43d40914')
    # 5. Create Condition resource on Primary Care EHR
    condition_resource = create_condition_resource(primary_patient_id=primary_patient_id, parent_id=parent_id, parent_term=parent_term)
    primary_condition_id = condition_resource.get('id')
    # 6. Create JSON files for validation
    create_patient_json_for_validation(primary_patient_id)
    create_condition_json_for_validation(primary_condition_id)