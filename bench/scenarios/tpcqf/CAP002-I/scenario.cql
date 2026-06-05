library BenchCAP002I version '1.0.0'
using FHIR version '4.0.1'
codesystem "SNOMED": 'http://snomed.info/sct'
valueset "Bench Condition ValueSet": 'http://example.com/fhir/ValueSet/bench-condition-vs'

context Patient
define "CountValueSetRetrieve":
  Count([Condition: "Bench Condition ValueSet"] C)
