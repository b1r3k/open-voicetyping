APP_VERSION := $(shell grep -oP '(?<=^version = ")[^"]*' pyproject.toml)
APP_DIR := voicetyping
NPROCS = $(shell grep -c 'processor' /proc/cpuinfo)
MAKEFLAGS += -j$(NPROCS)
PYTEST_FLAGS := --failed-first -x


install:
	poetry install
	test -d .git/hooks/pre-commit || poetry run pre-commit install

test:
	poetry run pytest ${PYTEST_FLAGS}

testloop:
	watch -n 3 poetry run pytest ${PYTEST_FLAGS}

lint-fix:
	poetry run ruff check --fix .

lint-check:
	poetry run ruff check ${APP_DIR}
	poetry run mypy .

sync-version:
	echo '__version__ = "$(APP_VERSION)"' > $(APP_DIR)/version.py
	git add $(APP_DIR)/version.py pyproject.toml
	git commit -m "Synced version to $(APP_VERSION)" || true

rename-project: NEW_APP_DIR :=$(shell echo ${NEW_APP_NAME} | tr '-' '_')
rename-project: APP_NAME := $(shell echo ${APP_DIR} | tr '_' '-')
rename-project:
	@echo "Renaming project ${APP_NAME} to ${NEW_APP_NAME}"
	@echo "Renaming directories ${APP_DIR} to ${NEW_APP_DIR}"
	mv ${APP_DIR} ${NEW_APP_DIR}
	find ./ -type f -not -path "./.git/*" -exec sed -i 's/${APP_DIR}/${NEW_APP_DIR}/g' {} \;
	find ./ -type f -not -path "./.git/*" -exec sed -i 's/${APP_NAME}/${NEW_APP_NAME}/g' {} \;


lint: lint-fix lint-check

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache .coverage .coverage.*
	find . -name "*.orig" -type f -delete
	find . -name "*.pyc" -type f -delete

# Debian packaging targets
debian-deps:
	sudo apt-get update
	sudo apt-get install -y debhelper dh-python pybuild-plugin-pyproject \
		python3-all python3-setuptools python3-poetry-core \
		portaudio19-dev libmp3lame-dev libudev-dev

debian-sync-version:
	@echo "Syncing debian version to $(APP_VERSION)..."
	sed -i '1s/(.*)/($(APP_VERSION)-1~trixie1)/' debian/changelog

debian-build: debian-sync-version
	dpkg-buildpackage -us -uc -b

debian-clean:
	dh_clean

debian-install: debian-build
	sudo dpkg -i ../open-voicetyping_*.deb

debian-lint:
	lintian ../open-voicetyping_*.deb

debian-test-install: debian-build
	# Test installation in current environment
	sudo dpkg -i ../open-voicetyping_*.deb
	@echo ""
	@echo "=== System service status ==="
	systemctl status voicetyping-keyboard@voicetyping.service --no-pager || true
	@echo ""
	@echo "=== Installed files ==="
	dpkg -L open-voicetyping | head -20
	@echo "... (truncated)"

debian-remove:
	sudo apt-get remove open-voicetyping

debian-purge:
	sudo apt-get purge open-voicetyping
