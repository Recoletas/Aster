.PHONY: test lint fmt type check run-console run-web

PYTHON := .venv/bin/python
RUFF := .venv/bin/ruff
MYPY := .venv/bin/mypy

test:            ## 运行全部离线测试
	$(PYTHON) -B -m unittest discover -s tests -v

lint:            ## 静态检查（ruff lint + 格式检查）
	$(RUFF) check aster tests
	$(RUFF) format --check aster tests

type:            ## 类型检查（mypy）
	$(MYPY)

fmt:             ## 自动修复与格式化
	$(RUFF) check --fix aster tests
	$(RUFF) format aster tests

check: lint type test  ## 提交前的完整质量门

run-console:     ## 本地 Web 之外的 Console 渠道（离线）
	$(PYTHON) -m aster.console

run-web:         ## 本地 Web 渠道（离线）
	$(PYTHON) -m aster.web_channel
