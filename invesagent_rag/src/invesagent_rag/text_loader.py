from __future__ import annotations

import hashlib
import re
from pathlib import Path

from invesagent_rag.schema import RagDocument, SourceFile


ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk")
MOJIBAKE_MARKERS = ("涓", "銆", "锛", "骞", "绗", "鍥", "�")


def file_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text_auto(path: Path) -> str:
    raw = path.read_bytes()
    candidates: list[tuple[int, str]] = []
    for encoding in ENCODINGS:
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        badness = sum(text.count(marker) for marker in MOJIBAKE_MARKERS)
        badness += text.count("\x00") * 10
        candidates.append((badness, text))
    if not candidates:
        return raw.decode("utf-8", errors="replace")
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def source_file(path: Path, root: Path) -> SourceFile:
    return SourceFile(
        path=path,
        relative_path=path.relative_to(root).as_posix(),
        md5=file_md5(path),
    )


def iter_txt_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.txt") if path.is_file())


def _infer_level(path: Path) -> str:
    path_text = path.as_posix()
    if "央级" in path_text:
        return "central"
    if "省级" in path_text:
        return "province"
    if "地级市" in path_text:
        return "prefecture"
    return "unknown"


def _infer_year(stem: str) -> int | None:
    match = re.search(r"(19|20)\d{2}", stem)
    return int(match.group(0)) if match else None


def _infer_region(stem: str, level: str, year: int | None) -> str:
    if level == "central":
        return "全国"
    if "_" in stem:
        return stem.split("_", 1)[0].strip()
    if year is not None:
        return stem.replace(str(year), "").strip("_ -")
    return stem


def load_policy_document(path: Path, root: Path) -> tuple[RagDocument, SourceFile]:
    src = source_file(path, root)
    text = read_text_auto(path)
    stem = path.stem
    level = _infer_level(path)
    year = _infer_year(stem)
    region = _infer_region(stem, level, year)
    title = f"{region}{year}年政府工作报告" if year else f"{region}政府工作报告"
    if level == "central":
        title = f"{year}年政府工作报告" if year else "政府工作报告"
    document = RagDocument(
        doc_id=src.md5,
        title=title,
        text=text,
        source_type="macro_policy",
        source_name="政府工作报告",
        source_path=src.relative_path,
        jurisdiction_level=level,
        region=region,
        year=year,
        published_at=int(f"{year}0101") if year else None,
        topics=["政府工作报告", "宏观政策", "财政政策", "产业政策", level, region],
    )
    return document, src


def load_company_report_document(path: Path, root: Path) -> tuple[RagDocument, SourceFile]:
    src = source_file(path, root)
    text = read_text_auto(path)
    stem = path.stem

    parts = stem.split("_")
    symbol = parts[0].strip() if len(parts) >= 1 else ""
    report_year = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else _infer_year(stem)
    company_name = parts[2].strip() if len(parts) >= 3 else ""
    report_type = parts[3].strip() if len(parts) >= 4 else "年度报告"
    published_at = None
    if len(parts) >= 5:
        date_text = parts[4].strip()
        if match := re.match(r"(\d{4})-(\d{2})-(\d{2})", date_text):
            published_at = int("".join(match.groups()))

    year_text = str(report_year) if report_year else ""
    if year_text and year_text in report_type:
        title_parts = [company_name, report_type]
    else:
        title_parts = [company_name, year_text, report_type]
    title = "".join(item for item in title_parts if item) or stem
    topics = ["公司年报", "年度报告", "财务报告"]
    topics.extend(item for item in (company_name, symbol, report_type) if item)

    document = RagDocument(
        doc_id=src.md5,
        title=title,
        text=text,
        source_type="company_report",
        source_name="上市公司年度报告",
        source_path=src.relative_path,
        jurisdiction_level="company",
        region="",
        year=report_year,
        published_at=published_at,
        market="cn",
        topics=topics,
        symbol=symbol,
        company_name=company_name,
        report_year=report_year,
        report_type=report_type,
    )
    return document, src
