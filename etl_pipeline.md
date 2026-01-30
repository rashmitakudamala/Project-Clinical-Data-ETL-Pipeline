
<link rel="stylesheet" href="assets/style.css">

# **ETL Pipeline page**

[Home](./index.md) ||
[ETL Pipeline](./etl_pipeline.md) ||
[Insights](./insights.md) ||
[Team Contributions](./team_contrib.md) ||
[About](./about.md) ||

## Introduction

This ETL pipeline demonstrates how clinical data can be exchanged, transformed, and re-loaded across different healthcare systems using FHIR, SNOMED CT, and HL7 v2 standards. The workflow begins by extracting Patient and Condition data from the OpenEMR FHIR server, retrieving SNOMED CT parent and child concepts from the Hermes Terminology Server, and transforming these resources into clean, standardized JSON structures. Each transformed resource is then loaded into the Primary Care EHR FHIR server, creating a parallel patient record in a separate environment. Additional tasks generate a structured Blood Pressure Observation and a SNOMED-coded Procedure to simulate common clinical documentation. The final task converts the transformed FHIR resources into a complete HL7 v2 ADT^A01 message, showing how modern API-based data can be adapted for legacy systems.

This page outlines each stage of the pipeline, explains the logic behind the five coding tasks, and shows how the components work together to achieve end-to-end clinical interoperability in your project.

---

## Technical Setup: APIs & Authentication

Our ETL pipeline communicates with three main services:

- **Source FHIR server (OpenEMR)**  
  `https://in-info-web20.luddy.indianapolis.iu.edu/apis/default/fhir`

- **Destination FHIR server (Primary Care EHR)**  
  `http://159.203.105.138:8080/fhir`

- **Hermes Terminology Server (SNOMED CT)**  
  `http://159.203.121.13:8080/v1/snomed`

Access to the OpenEMR FHIR API requires an OAuth2 access token. The token is stored locally in  
`src/data/access_token.json` and is read by our helper function before each API call.

### Example: building FHIR request headers with the access token

```python
from pathlib import Path
import json
import requests
from src.registration import data_dir

BASE_URL = "https://in-info-web20.luddy.indianapolis.iu.edu/apis/default/fhir"

def get_access_token_from_file():
    file_path = Path(data_dir / "access_token.json")
    with open(file_path, "r") as json_file:
        json_data = json.load(json_file)
    return json_data.get("access_token")

def get_headers():
    access_token = get_access_token_from_file()
    return {"Authorization": f"Bearer {access_token}"}

def get_patient(resource_id: str):
    url = f"{BASE_URL}/Patient/{resource_id}"
    response = requests.get(url=url, headers=get_headers())
    return response
```
This pattern is reused across tasks whenever we call the OpenEMR FHIR API.

---

### Error Handling

For each API call, we check the HTTP status code and handle missing or unexpected data. For example, in the Observation search:

```python
def search_observation(patient_resource_id: str):
    url = f"{BASE_URL}/Observation?patient={patient_resource_id}&code=http://loinc.org|85354-9"
    response = requests.get(url=url, headers=get_headers())
    print(response.url)

    if response.status_code != 200:
        # Basic error reporting for debugging
        print(f"Error when trying to access data: {response.status_code}")
        try:
            print("Error body:", response.json())
        except ValueError:
            print("Error body is not JSON")
        return None

    data = response.json()
    if "entry" not in data:
        print("No Observation resources found for this patient.")
        return None

    return data["entry"][0]["resource"]
```

This approach is used throughout the pipeline to avoid crashing when a bundle has no `entry` or when the server returns an error instead of a FHIR resource.

---

# **ETL Pipeline Documentation**

This project implements a complete clinical ETL pipeline that moves patient data, clinical conditions, vital signs, and procedures between two independent FHIR-based systems while applying terminology transformations using SNOMED CT. The workflow begins by extracting Patient and Condition resources from the OpenEMR FHIR server, retrieving parent and child SNOMED concepts from the Hermes Terminology Server, and transforming the data into standardized JSON resources suitable for the Primary Care EHR FHIR server. Additional tasks generate Observation and Procedure resources to simulate routine clinical documentation. The final stage of the pipeline converts FHIR data into an HL7 v2 ADT^A01 message, demonstrating interoperability with legacy systems.

Each of the five coding tasks builds on the previous one. Task 1 retrieves patient and condition data, applies a parent SNOMED transformation, and loads the cleaned Patient and Condition into the Primary EHR. Task 2 performs a similar transformation using a child SNOMED concept and loads a second Condition. Task 3 creates a structured blood pressure Observation using LOINC and SNOMED codes. Task 4 generates a SNOMED-coded Procedure for the same patient. Task 5 assembles an HL7 v2 message using mapped SNOMED-to-ICD-10 codes.
Together, these tasks form a full end-to-end interoperability pipeline that demonstrates how standardized APIs, clinical vocabularies, and Python-based tools can be used to transform and exchange clinical data across modern and legacy healthcare systems.

---

# **Task 1 - Parent Concept ETL**

Before performing the parent-concept transformation, Task 1 retrieves the Patient and Condition data from OpenEMR, enriches the Condition with a parent SNOMED concept using Hermes, and loads the cleaned Patient and transformed Condition into the Primary Care EHR. This section forms the foundation of the ETL pipeline.

<p align="center">
  <img src="assets/TASK%201.png" alt="Task 1 Flowchart" width="300">
</p>



## **Extract**

Task 1 retrieves:

* Filtered patient search using FHIR parameters
* A specific Patient by ID
* All Conditions for the patient
* The first Condition entry, including SNOMED code

## **Transform**

* Queries Hermes using `>!{snomed_code}` to obtain the **parent concept**
* Cleans the Patient resource (ID removal, SSN removal, address normalization)
* Builds a new Condition resource using the parent SNOMED concept

### Example Transformation Code (Task 1)

The patient resource from OpenEMR is cleaned before loading into the Primary FHIR server.
We remove metadata, drop any SSN identifier, and normalize the address text.

```python
def clean_patient_resource(raw_patient: dict) -> dict:
    # Remove server-specific metadata so the target FHIR server can assign its own
    raw_patient.pop("id", None)
    raw_patient.pop("meta", None)
    raw_patient.pop("extension", None)

    # Remove SSN identifier if present
    identifiers = raw_patient.get("identifier", [])
    for i, ident in enumerate(list(identifiers)):
        if "us-ssn" in ident.get("system", ""):
            identifiers.pop(i)
            break
    raw_patient["identifier"] = identifiers

    # Normalize address text and district
    if "address" in raw_patient and raw_patient["address"]:
        address = raw_patient["address"][0]
        if "district" not in address or not address["district"]:
            address["district"] = "Not found"

        line = (address.get("line") or [""])[0]
        city = address.get("city", "")
        district = address.get("district", "")
        state = address.get("state", "")
        postal = address.get("postalCode", "")

        address["text"] = f"{line} {city}, {district}, {state} {postal}".strip()

    return raw_patient
```

## **Load**

* POSTs the cleaned Patient to `/Patient`
* POSTs the transformed Condition to `/Condition`
* Generates `patient.json` and `parent_condition.json` for validation

### Example Load Code (Task 1)

```python
PRIMARY_FHIR_URL = "http://159.203.105.138:8080/fhir"

def post_patient_to_primary_care(patient: dict) -> dict:
    url = f"{PRIMARY_FHIR_URL}/Patient"
    headers = {"Content-Type": "application/fhir+json"}
    response = requests.post(url=url, headers=headers, json=patient)
    created_patient = response.json()
    print("Created Patient ID:", created_patient.get("id"))
    return created_patient
```

This pattern is reused for posting Condition, Observation, and Procedure resources in Tasks 1-4.

---

# **Task 2 - Child Concept ETL**

Task 2 extends the pipeline by retrieving the same patient's Condition and performing a downward SNOMED CT lookup to obtain a child concept. The child concept is then used to create another Condition in the Primary Care EHR.

<p align="center">
  <img src="assets/TASK%202.png" alt="Task 1 Flowchart" width="300">
</p>




## **Extract**

* GET Patient from OpenEMR
* GET all Conditions
* Extract the first Condition’s SNOMED code

## **Transform**

* Hermes lookup with `<!{snomed_code}` retrieves a **child concept**
* Builds a Condition resource using the child term

## **Load**

* Reads previously created `primary_patient_id.txt`
* POSTs the new Condition to the Primary Care EHR
* Saves `child_condition.json` with appropriate `meta.profile`

---

# **Task 3 - Observation ETL (Blood Pressure)**

Task 3 focuses on identifying existing BP Observations in OpenEMR, building a full vitals Observation if none exist, and loading it into the Primary Care EHR.

<p align="center">
  <img src="assets/TASK%203.png" alt="Task 1 Flowchart" width="300">
</p>



## **Extract**

* Searches OpenEMR using LOINC code `85354-9`
* Prints all matching Observation entries

## **Transform**

* Builds a full Observation JSON including:

  * LOINC panel and components
  * SNOMED equivalents
  * Body site, interpretation, practitioner
  * A unique identifier

## **Load**

* POSTs Observation to `/Observation`
* Saves created ID to `observation_id.txt`

---

# **Task 4 - Procedure ETL**

Task 4 checks OpenEMR for Procedure records and creates a structured Procedure resource linked to the Primary Care EHR patient.

<p align="center">
  <img src="assets/TASK%204.png" alt="Task 1 Flowchart" width="300">
</p>


## **Extract**

* GET all Procedure resources from OpenEMR
* Displays any entries found

## **Transform**

* Builds a SNOMED-coded Procedure:

  * Code: `180256009` (Subcutaneous immunotherapy)
  * Status, performer, dates, note, reason, follow-up

## **Load**

* POSTs Procedure resource to `/Procedure`
* Saves result to `procedure_id.txt`

---

# **Task 5 - HL7 v2 Message Generation**

Task 5 merges FHIR-native data with SNOMED and ICD-10 mapping to generate a complete HL7 ADT message using `hl7apy`.

<p align="center">
  <img src="assets/TASK%205.png" alt="Task 1 Flowchart" width="300">
</p>



## **Extract**

* Reads OpenEMR Patient JSON
* Loads `parent_condition.json`
* Retrieves SNOMED code and description

## **Transform**

* Maps SNOMED → ICD-10 using WHO refset **447562003**
* Constructs HL7 ADT^A01 message segments:

  * MSH - header
  * PID - identification
  * PV1 - visit
  * DG1 - diagnosis (ICD-10 + SNOMED term)

### Example SNOMED → ICD-10 Mapping (Task 5)

```python
BASE_HERMES_URL = "http://159.203.121.13:8080/v1/snomed"

def map_snomed_to_icd10(snomed_code: str, snomed_term: str):
    url = f"{BASE_HERMES_URL}/concepts/{snomed_code}/map/447562003"
    response = requests.get(url=url)
    data = response.json()
    mapping = data[0]
    icd10_code = mapping.get("mapTarget")
    icd10_term = snomed_term
    return icd10_code, icd10_term
```

The resulting ICD-10 code is then used to populate the `DG1` segment in the HL7 ADT^A01 message.

## **Load / Output**

* Saves the HL7 message to `adt_message.txt`
* Prints message in ER7 format

---

# **ETL Summary Overview**

Across the five tasks, this pipeline:

* Uses the OpenEMR FHIR server as the **source of truth** for the patient and their clinical data.
* Applies **terminology transformations** with SNOMED CT (parent/child concepts) and SNOMED → ICD-10 mappings using the Hermes Terminology Server.
* Creates a consistent set of **FHIR resources** (Patient, parent Condition, child Condition, Observation, Procedure) on a separate Primary Care EHR FHIR server.
* Generates a complete **HL7 v2 ADT^A01** message from the same data to support interoperability with legacy systems.

Together, these steps illustrate how a Python-based ETL pipeline can bridge multiple standards and systems while keeping the clinical meaning of the data intact.

---

# **Challenges and How We Resolved Them**

During development, we encountered several practical issues:

* **Missing or incomplete clinical data**
  Some patients in OpenEMR did not have blood pressure observations with LOINC `85354-9`.
  To handle this, Task 3 creates a new, well-structured Observation for the primary patient when no matching Observation is found, ensuring that the target FHIR server always has at least one blood pressure record for demonstration.

* **FHIR validation warnings and profile conformance**
  When validating `patient.json`, `parent_condition.json`, and `child_condition.json` against the Primary FHIR server, we initially encountered warnings related to missing narrative text and identifier types. We addressed these by:

  * Adding `meta.profile` entries to match the required StructureDefinitions
  * Including a simple `text.div` narrative for Condition resources
  * Adjusting identifier coding and address fields to align with the validator expectations

* **Terminology lookups and mappings**
  Understanding Hermes query syntax (e.g., `>!{code}` for parent and `<!{code}` for child) and the correct refset for SNOMED → ICD-10 mapping required some trial and error.
  Once the queries were confirmed, we standardized these lookups into helper functions used in Tasks 1, 2, and 5.

These challenges helped us better understand how to work with real-world FHIR APIs, validation rules, and terminology services in an end-to-end ETL pipeline.

---
<button id="backToTop" onclick="scrollToTop()">↑</button>
<script src="assets/back-to-top.js"></script>
