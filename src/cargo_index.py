"""Получение метаданных пакетов из sparse-индекса Cargo."""

import json
from http import HTTPStatus
from urllib.error import HTTPError
from urllib.request import urlopen

REQUEST_TIMEOUT = 20


def index_path(package):
    """Вычисляет путь к файлу пакета в индексе."""
    name = package.lower()
    short_prefixes = {1: "1", 2: "2", 3: f"3/{name[:1]}"}
    prefix = short_prefixes.get(len(name), f"{name[:2]}/{name[2:4]}")
    return f"{prefix}/{name}"


def read_index(repository, package):
    """Загружает записи обо всех версиях пакета по HTTP(S)."""
    url = f"{repository.rstrip('/')}/{index_path(package)}"
    try:
        with urlopen(url, timeout=REQUEST_TIMEOUT) as response:
            return [json.loads(line) for line in response if line.strip()]
    except HTTPError as error:
        if error.code == HTTPStatus.NOT_FOUND:
            raise ValueError(f"Пакет {package} не найден в индексе") from error
        raise


def get_release(repository, package, version):
    """Находит запись для точной версии пакета."""
    return find_release(read_index(repository, package), package, version)


def find_release(records, package, version):
    """Находит точную версию в уже загруженных записях."""
    for record in records:
        if record["vers"] == version:
            return record
    raise ValueError(f"Версия {version} пакета {package} не найдена")
