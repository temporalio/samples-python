worker:
	ls dan/*.py | entr -r poetry run python dan/utils/worker.py

.PHONY: worker
