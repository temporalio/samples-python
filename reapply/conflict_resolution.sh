NS=ns1
A=localhost:7233
B=localhost:8233
WID=my-workflow-id

start-workflow() {
    local addr=$1
    temporal workflow -n $NS --address $addr start --task-queue my-task-queue -w $WID --type my-workflow
}

terminate-workflow() {
    local addr=$1
    temporal workflow -n $NS --address $addr terminate -w $WID
}

send-signal() {
    local addr=$1
    local input=$2
    temporal workflow -n $NS --address $addr signal -w $WID --name my-signal --input "\"$input\""
}

run-worker() {
    local addr=$1
    ../sdk-python/.venv/bin/python ../samples-python/reapply/conflict_resolution.py $addr
}

send-update() {
    local addr=$1
    local input=$2
    temporal workflow -n $NS --address $addr update -w $WID --name my-update --input "\"$input\""
}

failover() {
    local cluster=$1
    tctl --ns $NS namespace update --active_cluster $cluster
}

enable-replication() {
    dc-set-replication-max-id 0
}

dc-set-replication-max-id() {
    local id=$1
    sed -i '/history.ReplicationMaxEventId:/,/value:/ s/value: .*/value: '$id'/' config/dynamicconfig/development-cass.yaml
    echo -n "Waiting 10s for dynamic config change..."
    sleep 10
    echo
}

list-events() {
    local addr=$1
    temporal workflow -n $NS --address $addr show --output json -w $WID |
        jq -r '.events[] | "\(.eventId) \(.eventType) \(.workflowExecutionSignaledEventAttributes.input[0])"'
}

list-events-both-clusters() {
    echo "cluster-a events:"
    list-events $A
    echo
    echo "cluster-b events:"
    list-events $B
}

if false; then
    make start-dependencies-cdc
    make install-schema-xdc

    # Start two unconnected clusters (see config/development-cluster-*.yaml)
    make start-xdc-cluster-a
    make start-xdc-cluster-b

    # Add cluster b as a remote of a
    # Add cluster a as a remote of b
    tctl --address $A admin cluster upsert-remote-cluster --frontend_address $B
    tctl --address $B admin cluster upsert-remote-cluster --frontend_address $A
    sleep 30
    # Register a multi-region namespace
    tctl --ns $NS namespace register --global_namespace true --active_cluster cluster-a --clusters cluster-a cluster-b
fi

if false; then

    start-workflow $A
    dc-set-replication-max-id 2
    send-signal $A A1
    list-events-both-clusters
    failover cluster-b
    dc-set-replication-max-id 3

    # failover

    # simulate conflict
    # re-enable replication
    send-signal $B 2
fi
