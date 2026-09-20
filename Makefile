.PHONY: setup data test dashboard

setup:
	python -m pip install -r requirements.txt

data:
	python -m src.pipeline

test:
	pytest -q

dashboard:
	streamlit run app.py

