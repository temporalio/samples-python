# Custom Metric

1. Run the server with `temporal server start-dev`
2. Run the client with `uv run custom_metric/client.py`
3. Run the workflow worker with `uv run custom_metric/workflow_worker.py`
4. Run the activity worker with `uv run custom_metric/activity_worker.py`
5. Go to `http://127.0.0.1:9090/metrics` in your browser

You'll get something like the following:

```txt
custom_activity_schedule_to_start_latency_bucket{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow",le="100"} 0
custom_activity_schedule_to_start_latency_bucket{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow",le="500"} 0
custom_activity_schedule_to_start_latency_bucket{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow",le="1000"} 0
custom_activity_schedule_to_start_latency_bucket{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow",le="5000"} 0
custom_activity_schedule_to_start_latency_bucket{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow",le="10000"} 1
custom_activity_schedule_to_start_latency_bucket{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow",le="100000"} 1
custom_activity_schedule_to_start_latency_bucket{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow",le="1000000"} 1
custom_activity_schedule_to_start_latency_bucket{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow",le="+Inf"} 1
custom_activity_schedule_to_start_latency_sum{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow"} 6336
custom_activity_schedule_to_start_latency_count{activity_type="print_message",namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",workflow_type="ExecuteActivityWorkflow"} 1
...
temporal_activity_schedule_to_start_latency_bucket{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",le="100"} 0
temporal_activity_schedule_to_start_latency_bucket{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",le="500"} 0
temporal_activity_schedule_to_start_latency_bucket{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",le="1000"} 0
temporal_activity_schedule_to_start_latency_bucket{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",le="5000"} 0
temporal_activity_schedule_to_start_latency_bucket{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",le="10000"} 1
temporal_activity_schedule_to_start_latency_bucket{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",le="100000"} 1
temporal_activity_schedule_to_start_latency_bucket{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",le="1000000"} 1
temporal_activity_schedule_to_start_latency_bucket{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue",le="+Inf"} 1
temporal_activity_schedule_to_start_latency_sum{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue"} 6336
temporal_activity_schedule_to_start_latency_count{namespace="default",service_name="temporal-core-sdk",task_queue="custom-metric-task-queue"} 1
```
