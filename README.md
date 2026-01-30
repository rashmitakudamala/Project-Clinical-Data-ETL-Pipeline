# Clinical Data ETL with FHIR, SNOMED CT, and HL7 v2

## Project Description

This project builds a small end-to-end **ETL (Extract-Transform-Load)** pipeline that moves clinical data between systems using standard healthcare interoperability tools:

- **FHIR** (Fast Healthcare Interoperability Resources) for Patient, Condition, Observation, and Procedure resources  
- **SNOMED CT** via the **Hermes Terminology Server** for concept lookups and parent/child relationships  
- **HL7 v2** via `hl7apy` for generating an `ADT^A01` message

The pipeline:

1. **Extracts** patient and condition data from an OpenEMR FHIR server and Hermes terminology server 
2. **Transforms** the data using SNOMED CT parent/child concepts and SNOMED to ICD-10 mappings  
3. **Loads** the transformed resources into a Primary Care EHR FHIR server  
4. Generates an **HL7 v2 ADT message** from the FHIR resources for legacy system exchange  

---

## Project Website

The project website generated from this repository can be accessed here:

👉 <https://pages.github.iu.edu/psurgi/FA25_B581_Final_Project_OpenEMR_Group4/>

---

## Repository Layout

- `src/`
  - `coding_task_1.py` - Extract Patient + Condition from OpenEMR, map the Condition code to a SNOMED **parent** concept using Hermes, create the Patient and parent Condition on the Primary FHIR server, and write `patient.json`, `parent_condition.json`, and `primary_patient_id.txt`.
  - `coding_task_2.py` - Use Hermes to retrieve a SNOMED **child** concept, create a child Condition on the Primary FHIR server, and write `child_condition.json`.
  - `coding_task_3.py` - Search for blood pressure Observations (LOINC `85354-9`); create a vital-signs Observation with systolic/diastolic components for the primary patient and `Practitioner/8`; save `observation.json` and `observation_id.txt`.
  - `coding_task_4.py` - Create a SNOMED-coded Procedure (“Subcutaneous immunotherapy”) for the primary patient and `Practitioner/8`; save `procedure.json` and `procedure_id.txt`.
  - `coding_task_5.py` - Load the primary Patient and parent Condition, map SNOMED → ICD-10 with Hermes, build an `ADT_A01` HL7 v2 message (`MSH`, `PID`, `PV1`, `DG1`) using `hl7apy`, and save `adt_message.txt`.
  - `validation.py` - Sends `$validate` requests to the Primary FHIR server for `patient.json`, `parent_condition.json`, and `child_condition.json`.
  - `registration.py` - Helper module (provided) that defines `data_dir` and shared configuration.
- `src/data/`
  - Contains generated JSON files and output artifacts.
- `.gitignore`
  - Ensures sensitive files such as `access_token.json`, `client_id`, `client_secret` are not committed.
- `requirements.txt`
  - Python package dependencies.
- `index.md`
  - Home page (project overview and presentation outline).
- `etl_pipeline.md` 
  - Detailed ETL pipeline documentation and task-by-task description.
- `insights.md` 
  - Project insights, challenges, lessons learned, and visualization.
- `team_contrib.md` 
  - Team roles, contributions, and individual reflections.
- `about.md` 
  - Short “About / Presentation” page for the team and project context.
- `README.md`

---

## Requirements / Dependencies

This project requires Python 3.x and the following packages (also listed in `requirements.txt`):

- `requests`  
- `hl7apy`  

A helper module `src/registration.py` defining `data_dir` and shared configuration.

Install everything with:

```bash
pip install -r requirements.txt
```

You will also need network access to:

- **OpenEMR FHIR server**  
  `https://in-info-web20.luddy.indianapolis.iu.edu/apis/default/fhir`

- **Primary Care EHR FHIR server**  
  `http://159.203.105.138:8080/fhir`

- **Hermes Terminology Server** (SNOMED CT)  
  `http://159.203.121.13:8080/v1/snomed`

An OAuth access token must be obtained using the client credentials (`client_id` and `client_secret`) provided.


## Setup

1. **Clone the repository**

```bash
git clone https://github.iu.edu/psurgi/test_project.git
cd test_project
```

2. **Create and activate a virtual environment (recommended)**

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

3. **Install Python dependencies**

All Python dependencies are listed in `requirements.txt` and can be installed with:

```bash
pip install -r requirements.txt
```

4. **Create the access token file (NOT tracked in git)**

Create `src/data/access_token.json` with your token:

```json
{
  "access_token": "YOUR_ACCESS_TOKEN_HERE"
}
```

This file is included in `.gitignore` and must **not** be pushed to GitHub.

---

## Instructions for Running the Scripts

Run the tasks **in order**, from the repository root, with your virtual environment activated.

### Task 1 - Create Patient + Parent Condition on Primary FHIR

```bash
python src/coding_task_1.py
```

Outputs:

* New Patient + Condition on the Primary FHIR server
* `src/data/primary_patient_id.txt`
* `src/data/patient.json`
* `src/data/parent_condition.json`

### Task 2 - Create Child Condition on Primary FHIR

```bash
python src/coding_task_2.py
```

Outputs:

* New child Condition on the Primary FHIR server
* `src/data/child_condition.json`

### Task 3 - Create Blood Pressure Observation

```bash
python src/coding_task_3.py
```

Outputs:

* New Observation linked to the primary patient and `Practitioner/8`
* `src/data/observation.json`
* `src/data/observation_id.txt`

### Task 4 - Create Procedure

```bash
python src/coding_task_4.py
```

Outputs:

* New Procedure linked to the primary patient and `Practitioner/8`
* `src/data/procedure.json`
* `src/data/procedure_id.txt`

### Task 5 - Generate HL7 v2 ADT^A01 Message

```bash
python src/coding_task_5.py
```

Outputs:

* `src/data/adt_message.txt` containing the HL7 v2 `ADT_A01` message.

### Validation Script

After running **Task 1** and **Task 2** (so that `patient.json`, `parent_condition.json`, and `child_condition.json` exist), you can validate the resources against the FHIR server:
```bash
python src/validation.py
```

This sends `$validate` requests for:

* `patient.json` (Patient)
* `parent_condition.json` (Condition)
* `child_condition.json` (Condition)

---

## Notes on Sensitive Data

* **Do not commit** OAuth access tokens or other secrets.
* `src/data/access_token.json` is intentionally excluded in `.gitignore`.
* Only push non-sensitive data and code (Python files, configuration, website files, etc.) to GitHub.

---