Instance: PatientTemplate
InstanceOf: Patient
* id = "{patient_id}"

Instance: ValueSetTemplate
InstanceOf: ValueSet
* id = "bench-condition-vs"
* url = "http://example.com/fhir/ValueSet/bench-condition-vs"
* version = "1.0.0"
* status = "active"
* name = "BenchConditionValueSet"
* compose.include[0].system = "http://snomed.info/sct"
* compose.include[0].concept[0].code = "38341003"
* compose.include[0].concept[0].display = "Hypertension"

* expansion.contains[0].system = "http://snomed.info/sct"
* expansion.contains[0].code = "38341003"
* expansion.contains[0].display = "Hypertension"

Instance: ConditionMatch
InstanceOf: Condition
* id = "cond-{patient_id}-m"
* subject = Reference(Patient/{patient_id})
* recordedDate = "2024-06-15T00:00:00Z"
* clinicalStatus.coding[0].system = "http://terminology.hl7.org/CodeSystem/condition-clinical"
* clinicalStatus.coding[0].code = "active"
* code.coding[0].system = "http://snomed.info/sct"
* code.coding[0].code = "38341003"

Instance: ObservationFinal
InstanceOf: Observation
* id = "obs-{patient_id}-final"
* status = "final"
* subject = Reference(Patient/{patient_id})
* code.coding[0].system = "http://snomed.info/sct"
* code.coding[0].code = "38341003"
* valueString = "match"
