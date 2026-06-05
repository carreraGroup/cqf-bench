library BenchCAP007I version '1.0.0'
using FHIR version '4.0.1'

context Patient
define "CountWithoutJoin":
  Count(
    [Condition] C
      without [Observation] O
        such that O.subject.reference.value = 'Patient/' + Patient.id.value
          and O.status.value = 'cancelled'
          and O.code ~ C.code
  )
