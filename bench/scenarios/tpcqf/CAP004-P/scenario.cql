library BenchCAP004P version '1.0.0'
using FHIR version '4.0.1'

context Patient
define "ReturnConditionIds":
  [Condition] R return R.id.value
