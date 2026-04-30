.PHONY: build run scrape extract metadata jupyter

IMAGE_NAME=steam-network-analysis

SEED ?= 76561198154174120
LIMIT ?= 10000000000

build:
	docker build -t $(IMAGE_NAME) .

run:
	docker run -it --rm -v "$(CURDIR):/app" $(IMAGE_NAME)

scrape:
	docker run -it --rm -v "$(CURDIR):/app" $(IMAGE_NAME) python -u src/main.py snowball --seed "$(SEED)" --limit $(LIMIT)

extract:
	docker run -it --rm -v "$(CURDIR):/app" $(IMAGE_NAME) python -u src/main.py extract --input data/edges.csv --output data/unique_games.csv

metadata:
	docker run -it --rm -v "$(CURDIR):/app" $(IMAGE_NAME) python -u src/main.py metadata --input data/unique_games.csv --output data/game_info.csv

jupyter:
	docker-compose up -d

down:
	docker-compose down
