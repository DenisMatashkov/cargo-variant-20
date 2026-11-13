"""Подбор версии по требованиям Cargo."""

import re
from operator import eq, ge, gt, le, lt

COMPARISONS = {"=": eq, ">": gt, ">=": ge, "<": lt, "<=": le}
TERM = re.compile(
    r"(>=|<=|[<>=~^])?\s*([0-9]+(?:\.[0-9]+){0,2})"
    r"(\.[*xX])?(-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?"
)


def version_key(version):
    """Возвращает ключ SemVer, игнорируя метаданные сборки."""
    core, _, prerelease = version.split("+", 1)[0].partition("-")
    identifiers = (
        (0, int(part)) if part.isdigit() else (1, part)
        for part in prerelease.split(".") if part
    )
    return tuple(map(int, core.split("."))), not prerelease, tuple(identifiers)


def parse_term(term):
    """Разбирает один оператор с полной или неполной версией."""
    if term in {"*", "x", "X"}:
        return "*", ((), True, ())
    match = TERM.fullmatch(term)
    if not match:
        raise ValueError(f"Неподдерживаемое требование версии: {term}")
    operator, core, wildcard, prerelease = match.groups()
    if wildcard:
        operator = "*"
    return operator or "^", version_key(core + (prerelease or ""))


def compare_version(candidate, operator, bound):
    """Сравнивает с полной или частичной версией."""
    core, stable, _ = candidate
    prefix = bound[0]
    if len(prefix) == len(core):
        return COMPARISONS[operator](candidate, bound)
    actual = core[:len(prefix)]
    if actual == prefix:
        return stable and operator in {"=", ">=", "<="}
    return COMPARISONS[operator](actual, prefix)


def matches_term(candidate, term):
    """Проверяет один оператор из требования Cargo."""
    operator, bound = term
    core, stable, prerelease = candidate
    prefix = bound[0]
    size = len(prefix)

    if operator == "*":
        return stable and core[:size] == prefix

    if operator in COMPARISONS:
        return compare_version(candidate, operator, bound)

    if operator == "~":
        fixed = prefix[:2]
    else:
        significant = next(
            (i for i, part in enumerate(prefix, start=1) if part), size
        )
        fixed = prefix[:significant]
    if core[:len(fixed)] != fixed:
        return False
    if operator == "^" and size < len(core):
        return core[:size] >= prefix
    return (core[:size], stable, prerelease) >= bound


def matching_versions(records, terms):
    """Возвращает доступные версии, удовлетворяющие требованиям."""
    eligible_prereleases = {bound[0] for _, bound in terms if not bound[1]}
    for record in records:
        if record.get("yanked"):
            continue
        version = record["vers"]
        key = version_key(version)
        core, stable, _ = key
        if not stable and core not in eligible_prereleases:
            continue
        if all(matches_term(key, term) for term in terms):
            yield version


def newest_version(records, requirement):
    """Выбирает максимальную подходящую версию, доступную в индексе."""
    terms = [parse_term(term.strip()) for term in requirement.split(",")]
    candidates = matching_versions(records, terms)
    version = max(candidates, key=version_key, default=None)
    if version is None:
        raise ValueError(f"Нет доступной версии для требования {requirement}")
    return version
