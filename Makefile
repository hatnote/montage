start:
	docker compose build && docker compose up

start-detached:
	docker compose build  && docker compose up -d

stop:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose down && docker compose up --build