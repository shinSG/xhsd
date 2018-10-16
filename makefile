init:
	pip install -r requirements.txt

run: init
	python bookinfo.py --file $(FILE)
