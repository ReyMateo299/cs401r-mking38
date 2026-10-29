You are an expert software engineering assistant helping me, the TA for CS 401r, build an automated grading pipeline for Lab 2. 

### Workspace Context
I have access to two main directories:
1. Instructor Repo: `dev_ta/cs401r-2026-instructor/` (Contains solutions, rubrics, instructions, and student submissions).
2. My TA Working Directory: `dev_ta/cs401r-mking38/` (Where I will store my scripts, plans, and output grades).
3. Tech Stack: Lab 2 submissions contain Python, Terraform, and a few other languages.

### Objective
We need to validate the existing grading workflow, cross-reference it with student instructions, and build an automated pipeline that uses static analysis to grade student submissions. We will test this pipeline on a single student before batch processing the rest.

### Execution Plan
Please read through these phases. We will execute them step-by-step. At the end of each phase, present your findings and STOP. Wait for my explicit approval before moving to the next phase.

**Phase 1: Discovery, Rubric Validation & Planning**
1. Search in `dev_ta/cs401r-2026-instructor/CS_401R_Labs/Sample Solutions/Lab Solution Notes/` for any files matching "Lab 2". Extract the grading rubric and the existing automated grading workflow.
2. Evaluate whether the existing grading workflow is sufficient to programmatically check *all* rubric items. 
3. Determine how to implement static analysis (e.g., using `tflint`, `flake8`, AST parsing, or custom script checks) to verify the key rubric points for the Python and Terraform files.
4. Create a planning document in `dev_ta/cs401r-mking38/grading/lab2/plan.md` outlining the pipeline architecture, the static analysis strategy, and noting any rubric items that must be graded manually.

**Phase 2: Instruction Cross-Check**
1. Read the student-facing instructions in `dev_ta/cs401r-2026-instructor/CS_401R_Labs/Lab_2--Data & Feature Engineering.md`.
2. Compare the instructions against the rubric from Phase 1.
3. Create a file at `dev_ta/cs401r-mking38/grading/lab2/rubric_discrepancies.md` listing any rubric items that were NOT clearly requested in the student instructions.

**Phase 3: Pipeline Construction**
1. Based on the approved plan, write the automated grading script(s) in `dev_ta/cs401r-mking38/grading/lab2/`. 
2. The script must integrate the static analysis checks for Python, Terraform, and the other languages to evaluate the code against the rubric.
3. The script must output a specific grade document containing the final score, a breakdown of specific rubric items, and the reasoning for any deductions.

**Phase 4: Single Student Test Run (Do Not Batch Grade Yet)**
1. Run the completed grading pipeline against exactly ONE student submission directory located in `dev_ta/cs401r-2026-instructor/grading/lab2/`.
2. Generate their grading document in `dev_ta/cs401r-mking38/grading/lab2/grades/<student_id>.md`.
3. Stop execution and ask me to review the generated grade document to ensure accuracy.

**Phase 5: Batch Execution**
1. Only after I approve the results of Phase 4, update or run the script to iterate through the remaining student submissions and generate their grade documents.

If you understand this plan, please acknowledge it, briefly summarize your understanding of the static analysis requirement and the single-student test constraint, and immediately begin Phase 1.