library BenchCAP011I version '1.0.0'
using FHIR version '4.0.1'

context Patient
define "LetCount":
  Count(
    [Condition] C
      let CId: C.id
      where CId is not null
  )
