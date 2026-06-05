library BenchCAP009I version '1.0.0'
using FHIR version '4.0.1'
include FHIRHelpers version '4.0.1' called FHIRHelpers
codesystem "SNOMED": 'http://snomed.info/sct'
valueset "Bench Condition ValueSet": 'http://example.com/fhir/ValueSet/bench-condition-vs'

context Patient
define function "ComplexMatch"(C Condition):
  C.recordedDate is not null
    and StartsWith(ToString(C.recordedDate), '2024')
    and exists(C.clinicalStatus.coding CS where CS.code = 'active')
    and Length(Coalesce(C.id, '')) > 5
    and C.code in "Bench Condition ValueSet"

define "ComplexPredicateCount":
  Count([Condition] C where "ComplexMatch"(C))
