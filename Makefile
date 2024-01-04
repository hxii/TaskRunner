install:
	pip install -r requirements.txt

lint:
	ruff check .
	ruff format . --check

fix:
	ruff check . --fix
	ruff format .

build: install lint
	# python -m build --sdist --wheel
	pyinstaller taskrunner.spec
