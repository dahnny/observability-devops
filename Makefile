.PHONY: up up-linux down logs ps validate

up:
	docker compose up -d --build

up-linux:
	docker compose -f docker-compose.yml -f docker-compose.linux.yml up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

ps:
	docker compose ps

validate:
	docker compose config
