# Healthcare Pipeline Data Directory

This directory contains source data for the healthcare pipeline project.

## Files

- `source_data.csv`: Source dataset containing synthetic patient encounter records.

## Dataset Schema

- `Name` (string): Patient full name
- `Age` (integer): Patient age in years
- `Gender` (string): Male / Female
- `Blood Type` (string): Blood group classification
- `Medical Condition` (string): Primary diagnosis (Arthritis, Asthma, Cancer, Diabetes, Hypertension, Obesity)
- `Date of Admission` (ISO date string): Admission date (`YYYY-MM-DD`)
- `Doctor` (string): Attending physician name
- `Hospital` (string): Treating facility name
- `Insurance Provider` (string): Payor organization (Aetna, Blue Cross, Cigna, Medicare, UnitedHealthcare)
- `Billing Amount` (float): Total billed amount ($)
- `Room Number` (integer): Assigned hospital room number
- `Admission Type` (string): Elective, Emergency, Urgent
- `Discharge Date` (ISO date string): Discharge date (`YYYY-MM-DD`)
- `Medication` (string): Prescribed medication
- `Test Results` (string): Lab test result outcome (Normal, Abnormal, Inconclusive)
