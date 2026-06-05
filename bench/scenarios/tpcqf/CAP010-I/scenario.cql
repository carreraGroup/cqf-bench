library BenchCAP010I version '1.0.0'
using FHIR version '4.0.1'
include FHIRHelpers version '4.0.1' called FHIRHelpers
codesystem "SNOMED": 'http://snomed.info/sct'
valueset "Bench Condition ValueSet": 'http://example.com/fhir/ValueSet/bench-condition-vs'

context Patient
define "ExistsManyResults":
  exists([Condition] C where C.code in "Bench Condition ValueSet")
