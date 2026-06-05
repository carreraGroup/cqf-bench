Instance: ConditionNoMatch
InstanceOf: Condition
* id = "cond-{patient_id}-n"
* subject = Reference(Patient/{patient_id})
* recordedDate = "2010-01-01T00:00:00Z"
* clinicalStatus.coding[0].system = "http://terminology.hl7.org/CodeSystem/condition-clinical"
* clinicalStatus.coding[0].code = "inactive"
* code.coding[0].system = "http://snomed.info/sct"
* code.coding[0].code = "90000001"

Instance: ObservationCancelled
InstanceOf: Observation
* id = "obs-{patient_id}-cancelled"
* status = "cancelled"
* subject = Reference(Patient/{patient_id})
* code.coding[0].system = "http://snomed.info/sct"
* code.coding[0].code = "90000001"
* valueString = "non-match"
