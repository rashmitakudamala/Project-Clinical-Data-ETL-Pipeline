from pathlib import Path

EMAIL = "sample@gmail.com"
URL = "https://in-info-web20.luddy.indianapolis.iu.edu/oauth2/default/registration"
SCOPE = "openid offline_access api:oemr api:fhir api:port user/allergy.read user/allergy.write user/appointment.read user/appointment.write user/dental_issue.read user/dental_issue.write user/document.read user/document.write user/drug.read user/encounter.read user/encounter.write user/facility.read user/facility.write user/immunization.read user/insurance.read user/insurance.write user/insurance_company.read user/insurance_company.write user/insurance_type.read user/list.read user/medical_problem.read user/medical_problem.write user/medication.read user/medication.write user/message.write user/patient.read user/patient.write user/practitioner.read user/practitioner.write user/prescription.read user/procedure.read user/soap_note.read user/soap_note.write user/surgery.read user/surgery.write user/transaction.read user/transaction.write user/vital.read user/vital.write user/AllergyIntolerance.read user/CareTeam.read user/Condition.read user/Coverage.read user/Encounter.read user/Immunization.read user/Location.read user/Medication.read user/MedicationRequest.read user/Observation.read user/Organization.read user/Organization.write user/Patient.read user/Patient.write user/Practitioner.read user/Practitioner.write user/PractitionerRole.read user/Procedure.read patient/Encounter.read patient/Patient.read patient/AllergyIntolerance.read patient/CareTeam.read patient/Condition.read patient/Coverage.read patient/Encounter.read patient/Immunization.read patient/MedicationRequest.read patient/Observation.read patient/Patient.read patient/Procedure.read"
REDIRECT_URI = "https://client.example.org/callback"
TOKEN_URL = "https://in-info-web20.luddy.indianapolis.iu.edu/oauth2/default/token"
data_dir = Path.cwd() / 'data'

def get_client_id_from_file():
    file_path = Path(data_dir / "client_id.txt")
    with open(file_path, 'r') as f:
        client_id = f.readline()
        if len(client_id) == 0:
            raise ValueError("ValueError - No client_id found in client_id.txt")
        else:
            return client_id


def get_client_secret_from_file():
    file_path = Path(data_dir / "client_secret.txt")
    with open(file_path, 'r') as f:
        client_secret = f.readline()
        if len(client_secret) == 0:
            raise ValueError("ValueError - No client_secret found in client_secret.txt")
        else:
            return client_secret