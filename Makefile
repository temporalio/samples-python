worker:
	ls dan/*.py | entr -r poetry run python dan/worker.py

.PHONY: worker
