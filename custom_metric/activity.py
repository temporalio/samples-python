import time

from temporalio import activity


@activity.defn
def print_and_sleep():
    print("In the activity.")
    time.sleep(1)
