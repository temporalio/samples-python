# Batch Sliding Window

This sample demonstrates a batch processing workflow that maintains a sliding window of record processing workflows.

A `SlidingWindowWorkflow` starts a configured number (sliding window size) of `RecordProcessorWorkflow` children in parallel. Each child processes a single record. When a child completes, a new child is started.

The `SlidingWindowWorkflow` calls continue-as-new after starting a preconfigured number of children to keep its history size bounded. A `RecordProcessorWorkflow` reports its completion through a signal to its parent, which allows notification of a parent that called continue-as-new.

A single instance of `SlidingWindowWorkflow` has limited window size and throughput. To support larger window size and overall throughput, multiple instances of `SlidingWindowWorkflow` run in parallel.

### Running This Sample

To run, first see [README.md](../README.md) for prerequisites. Then, run the following from root directory to start the worker:

    uv run batch_sliding_window/worker.py

This will start the worker. Then, in another terminal, run the following to execute the workflow:

    uv run batch_sliding_window/starter.py

The workflow will process 90 records using a sliding window of 10 parallel workers across 3 partitions, with a page size of 5 records per continue-as-new iteration.
