# Custom Metric

This sample deminstrates two things: (1) how to make a custom metric, and (2) how to use an interceptor.
The custom metric in this sample is an activity schedule-to-start-latency with a workflow type tag.

Please see the top-level README for prerequisites such as Python, uv, starting the local temporal development server, etc.

1. Run the worker with `uv run custom_metric/worker.py`
2. Request execution of the workflow with `temporal workflow start --type ExecuteActivityWorkflow --task-queue custom-metric-task-queue`
3. Go to `http://127.0.0.1:9090/metrics` in your browser

You'll get something like the following:

```txt
custom_activity_schedule_to_start_latency_bucket{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow",le="100"} 1
custom_activity_schedule_to_start_latency_bucket{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow",le="500"} 1
custom_activity_schedule_to_start_latency_bucket{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow",le="1000"} 1
custom_activity_schedule_to_start_latency_bucket{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow",le="5000"} 2
custom_activity_schedule_to_start_latency_bucket{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow",le="10000"} 2
custom_activity_schedule_to_start_latency_bucket{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow",le="100000"} 2
custom_activity_schedule_to_start_latency_bucket{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow",le="1000000"} 2
custom_activity_schedule_to_start_latency_bucket{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow",le="+Inf"} 2
custom_activity_schedule_to_start_latency_sum{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow"} 1010
custom_activity_schedule_to_start_latency_count{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow"} 2
...
temporal_activity_schedule_to_start_latency_bucket{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",le="100"} 1
temporal_activity_schedule_to_start_latency_bucket{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",le="500"} 1
temporal_activity_schedule_to_start_latency_bucket{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",le="1000"} 1
temporal_activity_schedule_to_start_latency_bucket{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",le="5000"} 2
temporal_activity_schedule_to_start_latency_bucket{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",le="10000"} 2
temporal_activity_schedule_to_start_latency_bucket{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",le="100000"} 2
temporal_activity_schedule_to_start_latency_bucket{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",le="1000000"} 2
temporal_activity_schedule_to_start_latency_bucket{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",le="+Inf"} 2
temporal_activity_schedule_to_start_latency_sum{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue"} 1010
temporal_activity_schedule_to_start_latency_count{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue"} 2
```
