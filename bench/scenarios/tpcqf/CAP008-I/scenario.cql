library BenchCAP008I version '1.0.0'
using FHIR version '4.0.1'

context Patient
define "SortedConditionIds":
  [Condition] C
    sort by id.value
