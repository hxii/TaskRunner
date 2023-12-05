install:
	pip install -r requirements.txt

build: install
	python -m build --sdist --wheel