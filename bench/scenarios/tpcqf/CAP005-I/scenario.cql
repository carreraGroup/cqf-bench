library BenchCAP005I version '1.0.0'
using FHIR version '4.0.1'
include FHIRHelpers version '4.0.1' called FHIRHelpers
codesystem "SNOMED": 'http://snomed.info/sct'
valueset "Bench Condition ValueSet": 'http://example.com/fhir/ValueSet/bench-condition-vs'

context Patient
define "BaseConditions":
  [Condition] C where C.code in "Bench Condition ValueSet"

define "TupleFromBase":
  Count(
    "BaseConditions" C
      return {
        id: Coalesce(C.id, ''),
        code: Coalesce(C.code.coding[0].code, '')
      }
  )
