# Update With Start: Lazy init

This sample illustrates the use of update-with-start to send Updates to a Workflow, starting the Workflow if
it is not running yet. The Workflow represents a Shopping Cart in an e-commerce application, and
update-with-start is used to add items to the cart, receiving back the updated cart subtotal.

Run the following from this directory:

    poetry run python worker.py

Then, in another terminal:

    poetry run python starter.py

This will start a worker to run your workflow and activities, then simulate a backend application receiving
requests to add items to a shopping cart, before finalizing the order.
