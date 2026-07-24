run-dev:
	uvicorn main:app --reload --port 8000

update-requirements:
	pip install -U -q pip-tools
	pip-compile --resolver=backtracking -o requirements/base/base.txt pyproject.toml
	pip-compile --resolver=backtracking --extra dev -o requirements/dev/dev.txt pyproject.toml

install-dev:
	@echo 'Installing pip-tools...'
	export PIP_REQUIRE_VIRTUALENV=true; \
	pip install -U -q pip-tools
	@echo 'Installing requirements...'
	pip-sync requirements/base/base.txt requirements/dev/dev.txt

setup:
	@echo 'Setting up the environment...'
	make install-dev

up:
	@echo 'Spinning up the whole stack...'
	docker compose up -d --build

down:
	@echo 'Shutting down the whole stack...'
	docker compose down

test:
	@echo 'Starting mongo for tests...'
	docker compose up -d --wait mongo
	MONGODB_URL=mongodb://localhost:27017/ pytest; EXIT_CODE=$$?; \
	echo 'Stopping and removing mongo and its volumes...'; \
	docker compose down -v; \
	exit $$EXIT_CODE

demo:
	@echo 'Serving the demo website...'
	npx http-server ./demo-website -p 3000