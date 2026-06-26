import threading
import time

from temporalio import activity
from custom_metric.shared import user_id


@activity.defn
def print_and_sleep():
    print(f"In the activity. in thread {threading.current_thread().name}")
    print(f"User ID: {user_id.get()} in activity {activity.info().activity_id}")
    time.sleep(1)
