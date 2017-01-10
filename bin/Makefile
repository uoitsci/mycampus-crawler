test:
	python dl-to-sqlite.py --db test.sqlite3 --semester 201701
	echo "select count(*) from schedule;" | sqlite3 test.sqlite3

debug:
	python -i dl-to-sqlite.py --db test.sqlite3 --semester 201701
