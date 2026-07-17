from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from temporalio.contrib.gcp import DEFAULT_METRIC_PERIODICITY

from gcp_open_telemetry.worker import WorkerSettings

SAMPLE_DIR = Path(__file__).parents[2] / "gcp_open_telemetry"


def test_plugin_default_metric_periodicity_is_sixty_seconds() -> None:
    assert DEFAULT_METRIC_PERIODICITY == timedelta(seconds=60)


def test_worker_settings_strip_secret_manager_newline() -> None:
    settings = WorkerSettings.from_environment(
        {
            "TEMPORAL_NAMESPACE": "example.a1b2c ",
            "TEMPORAL_TASK_QUEUE": "gcp-worker ",
            "TEMPORAL_API_KEY": "secret-token\n",
        }
    )

    assert settings.address == "example.a1b2c.tmprl.cloud:7233"
    assert settings.namespace == "example.a1b2c"
    assert settings.task_queue == "gcp-worker"
    assert settings.api_key == "secret-token"


def test_worker_settings_require_secret() -> None:
    with pytest.raises(RuntimeError, match="TEMPORAL_API_KEY"):
        WorkerSettings.from_environment(
            {
                "TEMPORAL_NAMESPACE": "example.a1b2c",
                "TEMPORAL_TASK_QUEUE": "gcp-worker",
                "TEMPORAL_API_KEY": "  ",
            }
        )


def test_collector_configuration_exports_metrics_and_traces() -> None:
    config = yaml.safe_load(
        (SAMPLE_DIR / "collector-config.yaml").read_text(encoding="utf-8")
    )

    assert config["receivers"]["otlp"]["protocols"]["grpc"]["endpoint"] == (
        "localhost:4317"
    )
    assert config["processors"]["resource_detection"]["detectors"] == ["gcp"]
    assert config["processors"]["batch/traces"]["timeout"] == "5s"
    metric_processors = config["service"]["pipelines"]["metrics"]["processors"]
    assert not any(
        processor.split("/", 1)[0] == "batch" for processor in metric_processors
    )
    assert config["service"]["pipelines"]["metrics"]["exporters"] == [
        "googlemanagedprometheus"
    ]
    assert config["service"]["pipelines"]["traces"]["processors"][-1] == (
        "batch/traces"
    )
    assert config["service"]["pipelines"]["traces"]["exporters"] == ["otlp_grpc"]
    assert config["exporters"]["otlp_grpc"]["endpoint"] == (
        "telemetry.googleapis.com:443"
    )


def test_worker_pool_uses_secret_environment_and_collector_probe() -> None:
    manifest = yaml.safe_load(
        (SAMPLE_DIR / "worker-pool.yaml").read_text(encoding="utf-8")
    )
    template = manifest["spec"]["template"]
    containers = {
        container["name"]: container for container in template["spec"]["containers"]
    }

    assert (
        template["metadata"]["annotations"]["run.googleapis.com/container-dependencies"]
        == '{"worker":["collector"]}'
    )
    assert containers["collector"]["args"] == ["--config=env:OTELCOL_CONFIG"]
    assert containers["collector"]["startupProbe"]["httpGet"] == {
        "path": "/",
        "port": 13133,
    }
    assert "volumeMounts" not in containers["collector"]
    assert (
        containers["worker"]["env"][-1]["valueFrom"]["secretKeyRef"]["name"]
        == "${TEMPORAL_API_KEY_SECRET}"
    )
