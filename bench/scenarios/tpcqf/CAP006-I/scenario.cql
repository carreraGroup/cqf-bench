library BenchCAP006I version '1.0.0'
using FHIR version '4.0.1'

context Patient
define "CountWithJoin":
  Count(
    [Condition] C
      with [Observation] O
        such that O.subject.reference.value = 'Patient/' + Patient.id.value
          and O.code ~ C.code
  )
