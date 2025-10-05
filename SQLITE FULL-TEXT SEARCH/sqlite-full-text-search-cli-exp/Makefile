PYTHON_VERSION:="3.13.7"

.PHONY: default
default: test ;


.PHONY : poetry-create-env
poetry-create-env:
	pyenv local $(PYTHON_VERSION) # It creates `.python-version`, to be git-ignored.
	poetry env use $$(pyenv which python) # It creates the env via pyenv.
	poetry install


.PHONY : poetry-destroy-env
poetry-destroy-env:
	rm -f poetry.lock
	@echo "Removing: $$(poetry run which python | tail -n 1)"
	poetry env remove $$(poetry run which python | tail -n 1)


.PHONY : poetry-destroy-and-recreate-env
poetry-destroy-and-recreate-env: poetry-destroy-env poetry-create-env


.PHONY : pyclean
pyclean:
	find . -name *.pyc -delete
	rm -rf *.egg-info build
	rm -rf coverage.xml .coverage
	find . -name .pytest_cache -type d -exec rm -rf "{}" +
	find . -name __pycache__ -type d -exec rm -rf "{}" +	


.PHONY : clean
clean: pyclean
	rm -rf build
	rm -rf dist


.PHONY : pip-clean
pip-clean:
	#rm -rf ~/Library/Caches/pip  # macOS.
	#rm -rf ~/.cache/pip  # linux.
	rm -rf $$(pip cache dir)  # Cross platform.


.PHONY : pip-uninstall-all
pip-uninstall-all:
	pip freeze | pip uninstall -y -r /dev/stdin


.PHONY : test
test:
	poetry run pytest -s tests/ -v -n auto --durations=5


.PHONY : format
format:
	isort .
	black .


.PHONY : format-check
format-check:
	isort --check-only .
	black --check .
