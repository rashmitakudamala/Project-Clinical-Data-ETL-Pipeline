import json
import requests
from pathlib import Path
from src.registration import data_dir

PRIMARY_FHIR_URL = "http://159.203.105.138:8080/fhir" # Primary FHIR EHR server

def validate_resource(file_name: str, resource_type: str):
    """
       Validate a local FHIR resource JSON file against the PRIMARY_FHIR_URL server.
   """
    # Load the resource from data/<file_name>.json
    with open(data_dir / f"{file_name}.json") as f:
        resource = json.load(f)

    # Call the $validate operation on the FHIR server
    response = requests.post(
        f"{PRIMARY_FHIR_URL}/{resource_type}/$validate",
        headers={"Content-Type": "application/fhir+json"},
        json=resource,
    )
    # Print HTTP status and the OperationOutcome details
    print(response.status_code)
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    print()
    # Validate the Patient and both Condition profiles created in Task 1 & 2
    validate_resource("patient", "Patient")
    print()
    validate_resource("parent_condition", "Condition")
    print()
    validate_resource("child_condition", "Condition")
