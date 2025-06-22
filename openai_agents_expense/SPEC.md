This test extends the Temporal expense example with OpenAI Agents SDK.

The structure flow will be the same as in /expense, however we will make the example more interesting by adding ai-based expense categorization.
We will also add AI-aided approval, i.e., we will use an agent to compare the expense against multiple sets ofo rules
- one set of rules is basic departmental policies
- one set of rules is designed to protect against fraud
At the end of the process, the expense submitter will receive a message telling them whether their expense was approved or rejected
It is important that that anti-fraud rules are not exfiltrated from the model, i.e., use guardrails to make sure that that nothing inappropriate escapes
Also use guardrails to ensure that the submitted expense is actually an expense report.

Note that we generally want to keep things simple / illustrative because this is designed to be a sample.
The purpose of this sample is to show the benefits of combining Temporal with the OpenAI Agents SDK.