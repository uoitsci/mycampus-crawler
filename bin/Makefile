timestamp = $(shell date +'%Y-%m-%d')
all:
	python dl-to-sqlite.py --db ../databases/$(timestamp).sqlite3 --semester all

test:
	python dl-to-sqlite.py --db test.sqlite3 --semester 201701
	echo "select count(*) from schedule;" | sqlite3 test.sqlite3

debug:
	python -i dl-to-sqlite.py --db test.sqlite3 --semester 201701

clean:
	rm -rf *.pyc
