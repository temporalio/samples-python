worker:
	ls dan/*.py | entr -r uv run python dan/utils/worker.py

.PHONY: worker
