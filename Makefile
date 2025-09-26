APP=blockshelf
PY?=python3
VENV?=.venv
DJANGO?=$(VENV)/bin/python manage.py
GUNICORN?=$(VENV)/bin/gunicorn
WSGI?=blockshelf_inventory.wsgi:application

.PHONY: venv install dev run migrate superuser collectstatic check test shell systemd-* logs

venv:
	@test -d $(VENV) || $(PY) -m venv $(VENV)

install: venv
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt
	$(VENV)/bin/pip install gunicorn

dev:
	$(DJANGO) runserver 0.0.0.0:8000

run:
	$(GUNICORN) -c gunicorn.conf.py $(WSGI)

migrate:
	$(DJANGO) migrate

superuser:
	$(DJANGO) createsuperuser

collectstatic:
	$(DJANGO) collectstatic --noinput

check:
	$(DJANGO) check --deploy

test:
	$(DJANGO) test

shell:
	$(DJANGO) shell

systemd-start:
	sudo systemctl start $(APP)

systemd-stop:
	sudo systemctl stop $(APP)

systemd-restart:
	sudo systemctl restart $(APP)

systemd-status:
	systemctl status $(APP)

logs:
	journalctl -u $(APP) -n 200 -f
