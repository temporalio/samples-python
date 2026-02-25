
# Request/Response Sample with Activity-Based Responses 

This sample demonstrates how to send a request and get a response from a Temporal workflow via a response activity.

In this example, the workflow accepts requests (signals) to uppercase a string and then provides the response via a callback response activity. Because the response is delivered by an activity execution, the requester must have its own worker running.

## Running

Follow these steps to run the sample:

1. **Run a [Temporal service](https://github.com/temporalio/samples-go/tree/main/#how-to-use):**  

2. **Run the Worker:**  
   In one terminal, run the worker that executes the workflow and activity:
   ```bash
   python worker.py
   ```

3. **Start the Workflow:**  
   In another terminal, start the workflow instance:
   ```bash
   python starter.py
   ```

4. **Run the Requester:**  
   In a third terminal, run the requester that sends a request every second:
   ```bash
   python requester_run.py
   ```
   This will send requests like `foo0`, `foo1`, etc., to be uppercased by the workflow. You should see output similar to:
   ```
   Requested uppercase for 'foo0', got: 'FOO0'
   Requested uppercase for 'foo1', got: 'FOO1'
   ...
   ```

Multiple instances of these processes can be run in separate terminals to confirm that they work independently.

## Comparison with Query-Based Responses

In the [reqrespquery](../reqrespquery) sample, responses are fetched by periodically polling the workflow using queries. This sample, however, uses activity-based responses, which has the following pros and cons:

**Pros:**

* Activity-based responses are often faster due to pushing rather than polling.
* The workflow does not need to explicitly store the response state.
* The workflow can detect whether a response was actually received.

**Cons:**

* Activity-based responses require a worker on the caller (requester) side.
* They record the response in history as an activity execution.
* They can only occur while the workflow is running.

## Explanation of Continue-As-New

Workflows have a limit on history size. When the event count grows too large, a workflow can return a `ContinueAsNew` error to atomically start a new workflow execution. To prevent data loss, signals must be drained and any pending futures completed before a new execution starts. 

In this sample, which is designed to run long-term, a `ContinueAsNew` is performed once the request count reaches a specified limit, provided there are no in-flight signal requests or executing activities. (If signals are processed too quickly or activities take too long, the workflow might never idle long enough for a `ContinueAsNew` to be triggered.) Careful tuning of signal and activity handling (including setting appropriate retry policies) is essential to ensure that the workflow can transition smoothly to a new execution when needed.

## License

This sample is released under the MIT License.
