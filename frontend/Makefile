.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z_%-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-28s\033[0m %s\n", $$1, $$2}'

.PHONY: install dev test test-coverage lint api

install:                ## pnpm install
	pnpm install

dev:                    ## Vite dev server
	pnpm run dev

test:                   ## vitest, one run
	pnpm run test:unit run

test-coverage:          ## vitest with coverage: terminal summary + HTML report in coverage/index.html
	pnpm run test:coverage

lint:                   ## ESLint with auto-fix
	pnpm run lint

api:                    ## regenerate src/backend/ from ../openapi.json
	pnpm run api
