PY ?= python3
export PYTHONPATH := src

.PHONY: run extract load transform quality test lint analysis clean docker

run:        ## full pipeline: extract -> load -> transform -> quality
	$(PY) -m pipeline.run all --days 30
extract:
	$(PY) -m pipeline.run extract --days 30
load:
	$(PY) -m pipeline.run load
transform:
	$(PY) -m pipeline.run transform
quality:
	$(PY) -m pipeline.run quality
test:
	$(PY) -m pytest -q
lint:
	ruff check src tests dags
analysis:   ## run the business-question queries against the warehouse
	sqlite3 -header -column data/warehouse.db < sql/analysis/business_questions.sql
clean:
	rm -rf data/raw data/warehouse.db
docker:
	docker build -t ecommerce-elt . && docker run --rm -v $$(pwd)/data:/app/data ecommerce-elt
