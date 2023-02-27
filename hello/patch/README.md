# Patch Workflow Sample
This sample will demonstrate how to version a workflow. The sample workflow will execute a activity and fire a timer. 

- First run the v1 workflow
- Ctrl-C and interrupt workflow
- Run the v2 workflow
 - The workflow will is running, execution resumes (after timer fires) and your v1 code is run
- Re-run the v2 workflow
 - The workflow will execute your new v2 code
