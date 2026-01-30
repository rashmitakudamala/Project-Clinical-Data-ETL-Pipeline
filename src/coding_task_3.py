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

def search_observation(patient_resource_id):
    """
        Check OpenEMR for any existing blood pressure Observations for the patient,
        using LOINC 85354-9 (Blood pressure panel).
        Returns the first Observation resource () if found, otherwise None.
    """
    url = f'{BASE_URL}/Observation?patient={patient_resource_id}&code=http://loinc.org|85354-9'
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
            # Return the first Observation resource
            return entry[0]['resource']
        else:
            print('No Condition resource found')
            return None
    else:
        print(f"Error when trying to access data: {response.status_code}")
        try:
            print(f'Error: {response.json()}')
        except ValueError:
            print(f"Error body is not JSON")
        return None

def create_observation(patient_id):
    """
       Create a blood pressure Observation JSON for the given PRIMARY EHR patient id.
    """
    observation = {
        "resourceType": "Observation",
        "meta": {
            "profile": ["http://hl7.org/fhir/StructureDefinition/vitalsigns"]
        },
        "identifier": [
            {
                "system": "urn:ietf:rfc:3986",
                "value": "urn:uuid:187e0c12-8dd2-67e2-99b2-bf273c878281"
            }
        ],
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "85354-9",
                "display": "Blood pressure panel with all children optional"
            }],
            "text": "Blood pressure systolic & diastolic"
        },
        "subject": {
            "reference": f"Patient/{patient_id}"
        },
        "performer": [
            {
                "reference": "Practitioner/8",
                "display": "Dr. Careful"
            }
        ],
        "effectiveDateTime": "2025-11-27",
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "N",
                "display": "Normal"
            }],
            "text": "Normal"
        }],
        "bodySite": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": "368209003",
                "display": "Right arm"
            }]
        },
        "component": [{
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "8480-6",
                    "display": "Systolic blood pressure"
                },
                    {
                        "system": "http://snomed.info/sct",
                        "code": "271649006",
                        "display": "Systolic blood pressure"
                    }]
            },
            "valueQuantity": {
                "value": 120,
                "unit": "mmHg",
                "system": "http://unitsofmeasure.org",
                "code": "mm[Hg]"
            },
            "interpretation": [{
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                    "code": "N",
                    "display": "normal"
                }],
                "text": "Normal"
            }]
        },
            {
                "code": {
                    "coding": [{
                        "system": "http://loinc.org",
                        "code": "8462-4",
                        "display": "Diastolic blood pressure"
                    },
                        {
                            "system": "http://snomed.info/sct",
                            "code": "271650006",
                            "display": "Diastolic blood pressure"
                        }
                    ]
                },
                "valueQuantity": {
                    "value": 80,
                    "unit": "mmHg",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm[Hg]"
                },
                "interpretation": [{
                    "coding": [{
                        "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                        "code": "N",
                        "display": "normal"
                    }],
                    "text": "Normal"
                }]
            }]
    }
    # Save a copy for validation
    with open(data_dir / "observation.json", "w") as f:
        json.dump(observation, f, indent=2)
    return observation

def post_observation_to_primary_fhir(observation):
    """
        POST the Observation resource to the Primary Care EHR FHIR server.
        Also prints and saves the created Observation id to observation_id.txt.
    """
    fhir_url = f'{PRIMARY_FHIR_URL}/Observation'
    headers = {'Content-Type': 'application/fhir+json'}
    print(f'POST {fhir_url}')
    response = requests.post(url=fhir_url, headers=headers, json=observation)
    print(response.url)

    created_observation = response.json()
    print(created_observation)
    print("Created Observation resource on primary care EHR:")
    resource_type = created_observation.get('resourceType')
    resource_id = created_observation.get('id')
    code = created_observation['code']['coding'][0]['code']
    display = created_observation['code']['coding'][0]['display']

    # Save Observation id
    with open(data_dir / "observation_id.txt", "w") as f:
        f.write(str(resource_id))
    print(f'Resource type: {resource_type}')
    print(f'Resource ID: {resource_id}')
    print(f'Code: {code}')
    print(f'Display: {display}')
    print()
    return created_observation
if __name__ == '__main__':
    print()
    # 1. Load the Primary Care EHR patient id saved from Task 1
    patient_id = load_patient_id_from_file()
    # 2. Check OpenEMR to see if a BP Observation already exists
    search_observation(patient_resource_id='9d036484-c661-485c-899d-fcab43d40914')
    # 3. Create a new BP Observation for the primary_patient_id
    observation_resource = create_observation(patient_id=patient_id)
    # 4. POST the Observation to the Primary Care EHR server
    post_observation_to_primary_fhir(observation= observation_resource)
