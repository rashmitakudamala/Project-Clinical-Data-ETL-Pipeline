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

def search_condition(patient_resource_id):
    """
        List all Condition resources in OpenEMR for a given patient.
        Prints resourceType, Condition id, and SNOMED code for each entry.
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

def get_child_for_code(patient_resource_id):
    """
        Retrieve the first Condition for the patient from OpenEMR,
        extract its SNOMED code, and query Hermes for a child concept.

        Returns (child_id, child_term) if found,
        or (None, None) if no child concept was returned.
    """
    # Get the base Condition from OpenEMR
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
    else:
        print('No Condition resources found for this patient')
        return None, None

    # Use Hermes terminology server to get a child SNOMED concept
    snomed_url = f'{BASE_HERMES_URL}/search?constraint=<!{code}'
    response = requests.get(url=snomed_url)
    print(response.url)
    data = response.json()
    if data:
        child_id = data[0].get('conceptId')
        child_term = data[0].get('preferredTerm')
        print(f"Child concept for selected condition: {code}")
        print(f'Child concept ID: {child_id}')
        print(f'Child preferred term: {child_term}')
        print()
        return child_id, child_term
    else:
        print('No results found')
        return None, None

CONDITION_PROFILE_URL = "http://example.org/StructureDefinition/my-condition-profile"
def create_condition_resource(primary_patient_id, child_id, child_term):
    """
        Build a Condition resource using the child SNOMED concept returned from Hermes
        and create it on the Primary Care EHR linked to the primary_patient_id.
    """
    condition_resource = {
        "resourceType": "Condition",
        "text": {
            "status": "generated",
            "div": (
                '<div xmlns="http://www.w3.org/1999/xhtml">'
                f"<p>{child_term}</p>"
                "</div>"
            )
        },
        "clinicalStatus": {
            "coding": [
                {
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": "active",
                    "display": "Active"
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
                    "code": child_id,
                    "display": child_term
                }
            ],
            "text": child_term
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
        "onsetDateTime": "2014-06-01",

        "subject": {
            "reference": f"Patient/{primary_patient_id}"
        }
    }

    # POST new Condition to the Primary Care EHR
    fhir_url = f'{PRIMARY_FHIR_URL}/Condition'
    headers = {'Content-Type': 'application/json'}
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

def create_condition_json_for_validation(primary_condition_id):
    """
        Read the child Condition from Primary Care EHR, attach the profile URL,
        and write it to child_condition.json for validation.
    """
    url = f'{PRIMARY_FHIR_URL}/Condition/{primary_condition_id}'
    response = requests.get(url=url)
    print(url)
    data = response.json()

    # Attach Condition profile
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

    # Ensure category is set to encounter-diagnosis
    category_coding = {
        "system": "http://terminology.hl7.org/CodeSystem/condition-category",
        "code": "encounter-diagnosis",
        "display": "Encounter Diagnosis"
    }

    if "category" in data and data["category"]:
        # overwrite first category coding
        data["category"][0]["coding"] = [category_coding]
    else:
        data["category"] = [
            {
                "coding": [category_coding]
            }
        ]

    # Save final JSON for validation
    with open(data_dir / "child_condition.json", "w") as f:
        json.dump(data, f, indent=2)

    print("Created child_condition.json for validation")
    print()


if __name__ == '__main__':
    print()
    # 1. Show the source patient in OpenEMR
    get_fhir_patient(resource_id='9d036484-c661-485c-899d-fcab43d40914')
    # 2. Inspect all Conditions on OpenEMR for this patient
    search_condition(patient_resource_id='9d036484-c661-485c-899d-fcab43d40914')
    get_one_condition(patient_resource_id='9d036484-c661-485c-899d-fcab43d40914')
    # 3. Get child SNOMED concept from Hermes based on patient's Condition
    get_child_for_code(patient_resource_id='9d036484-c661-485c-899d-fcab43d40914')
    child_id, child_term = get_child_for_code(patient_resource_id='9d036484-c661-485c-899d-fcab43d40914')
    # 4. Read the primary_patient_id that was created in Task 1
    with open(data_dir / "primary_patient_id.txt", "r") as f:
        primary_patient_id = f.read().strip()
    # 5. Create child Condition resource on Primary Care EHR
    condition_resource = create_condition_resource(primary_patient_id=primary_patient_id, child_id=child_id, child_term=child_term)
    primary_condition_id = condition_resource.get('id')
    # 6. Export child_condition.json for validation
    create_condition_json_for_validation(primary_condition_id)