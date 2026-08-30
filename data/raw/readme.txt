The FJSP-F benchmark test suite is provided in this file.

The LLG-F includes 20 instances (LLG-F1 to LLG-F20) with various scales ranging from three jobs, four machines, and two fixtures to 20 jobs, ten machines, and 12 fixtures.

------------------------------------------------------

The meaning of the main variables:
1. dt: The delivery time of each job
2. Jm: The eligible machine set of each operation.
3. JmNumber: The total number of the machines
4. Jf: The eligible fixture set of each operation.
5. pjob: The priority of each job.
6. rt: The release time of each job.
7. T: The processing time of each operation.
8. fixnumbegin: The number of Type I fixtures of each fixture (The number of each fixture in inventory)
9. fixnumend: The sum of the number of Type I fixtures and Type II fixtures of each fixture (The number of each fixture after the production)
10. fixtype1: Categories of Type I fixtures
11. fixtype2: Categories of Type II fixtures
12. fixtype1seq: Sequences of Type I fixtures
13. fixtypewseq: Sequences of Type I fixtures

