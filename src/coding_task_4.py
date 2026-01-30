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


def load_patient_id_from_file():
    """
        Load the PRIMARY EHR patient id (created in Task 1) from
        primary_patient_id.txt so we can attach the Observation to that patient.
    """
    try:
        with open(data_dir / "primary_patient_id.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        print("Error: patient_id.txt not found.")
        return None


def search_procedure(patient_resource_id):
    """
       Search OpenEMR for existing Procedure resources for the given OpenEMR patient id.
       Prints any found Procedure resources.
       """
    url = f'{BASE_URL}/Procedure?patient={patient_resource_id}'
    response = requests.get(url=url, headers=get_headers())
    print(response.url)
    if response.status_code == 200:
        data = response.json()
        if 'entry' in data:
            print(f"Number of entries: {len(data['entry'])}")
            print()
            entry = data.get('entry')
            for item in entry:
                pprint(item)
                resource_type = item['resource']['resourceType']
                resource_id = item['resource']['id']
                print(f'Resource type: {resource_type}')
                print(f'Resource ID: {resource_id}')
        else:
            print('No Procedure resource found')
    else:
        print(f"Error when trying to access Procedure data: {response.status_code}")
        try:
            print("Error body:", response.json())
        except ValueError:
            print("No JSON body in error response.")
        return None


def create_procedure(patient_id):
    """
        Create a Procedure resource for the given PRIMARY EHR patient id.
        This procedure is linked to SNOMED code, subject, performer
        """
    procedure = {
        "resourceType": "Procedure",
        "meta": {
            "versionId": "1"
        },
        "text": {
            "status": "generated",
            "div": (
                "<div xmlns=\"http://www.w3.org/1999/xhtml\">"
                "Subcutaneous allergen immunotherapy for perennial allergic rhinitis"
                "</div>"
            )
        },
        "status": "completed",
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "180256009",
                    "display": "Subcutaneous immunotherapy"
                }
            ],
            "text": "Subcutaneous immunotherapy"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "performedDateTime": "2008-09-04",
        "performer": [
            {
                'actor': {
                    "reference": "Practitioner/8",
                    "display": "Dr. Careful"
                }
            }
        ],
        "reasonCode": [
            {"concept": {
                "text": "Perennial allergic rhinitis not controlled with medication"
            }
        }],
        "followUp": [
            {
                "text": "Follow-up visit in 4 weeks"
            }
        ],
        "note": [
            {
                "text": "First dose of maintenance allergen immunotherapy administered without complications."
            }
        ]
    }

    # Save Procedure JSON to file for validation
    with open(data_dir / "procedure.json", "w") as f:
        json.dump(procedure, f, indent=2)
    return procedure


def post_procedure_to_primary_fhir(procedure):
    """
        POST the Procedure resource to the Primary Care EHR FHIR server.
        Also prints and saves the created Procedure id to procedure_id.txt.
    """
    fhir_url = f'{PRIMARY_FHIR_URL}/Procedure'
    headers = {'Content-Type': 'application/fhir+json'}
    print(f'POST {fhir_url}')
    response = requests.post(url=fhir_url, headers=headers, json=procedure)
    print(response.url)

    created_procedure = response.json()
    print(created_procedure)
    print("Created Procedure resource on primary care EHR:")
    resource_type = created_procedure.get('resourceType')
    resource_id = created_procedure.get('id')
    code = created_procedure['code']['coding'][0]['code']
    display = created_procedure['code']['coding'][0]['display']

    # Save the new Procedure id
    with open(data_dir / "procedure_id.txt", "w") as f:
        f.write(str(resource_id))
    print(f'Resource type: {resource_type}')
    print(f'Resource ID: {resource_id}')
    print(f'Code: {code}')
    print(f'Display: {display}')
    print()


if __name__ == '__main__':
    print()
    # 1. Load primary_patient_id created in Task 1
    patient_id = load_patient_id_from_file()
    # 2. Check OpenEMR for any existing Procedure resources for the original patient
    search_procedure(patient_resource_id='9d036484-c661-485c-899d-fcab43d40914')
    # 3. Create a Procedure resource for the PRIMARY EHR patient
    procedure_resource = create_procedure(patient_id=patient_id)
    # 4. POST the Procedure to the Primary Care EHR FHIR server
    post_procedure_to_primary_fhir(procedure=procedure_resource)
