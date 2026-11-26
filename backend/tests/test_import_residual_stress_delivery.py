"""The import of a residual stress delivery into the data repo (#228).

A tiny fake data repo (one hot-rolled record, committed) and a fake delivery
(the same record plus one built-up record) with the problems of the real
2026-11-17 delivery: CRLF, two encodings in one file, C1 quote characters, the
``steel-web`` name, the capitalised distribution header, an empty file.
No database.
"""

import subprocess
from pathlib import Path

from data.import_residual_stress_delivery import fix_c1, main
from resslab_hub.data.residual_stress_qp import BUILT_UP_QP_COLUMNS

DICTIONARY_HEADER = (
    "column_name,description,symbol,unit,type,example_value,nullable,group"
)
# U+0093 and U+0094 are how the repo stored Windows quotes before the fix.
OLD_REFERENCE = "\u0093The title.\u0094 Journal"
HOT_ROLLED_QP = "qp_coefficient\n30.9\n-0.05\n26.8\n0.002\n"
BUILT_UP_QP = (
    ",".join(BUILT_UP_QP_COLUMNS)
    + "\n"
    + ",".join(["1"] * len(BUILT_UP_QP_COLUMNS))
    + "\n"
)


def write(path: Path, content, newline: str = "\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        content = content.replace("\n", newline).encode("utf-8")
    path.write_bytes(content)


def make_repo(root: Path) -> Path:
    folder = root / "residual_stresses"
    write(
        folder / "residual_stresses.csv",
        "id,profile_type,reference,data_curation_status\n"
        f'HR1,Hot-rolled wide flange,"{OLD_REFERENCE}",verified\n',
    )
    write(
        folder / "residual_stresses_data_dictionary.csv",
        f"{DICTIONARY_HEADER}\n"
        "id,Identifier,,-,String,HR1,False,Experimental program details\n"
        "profile_type,Type,,-,String,Hot,False,Steel profile\n"
        "reference,Citation,,-,String,X,False,Experimental program details\n"
        "data_curation_status,Status,,-,String,verified,False,"
        "Experimental program details\n",
    )
    write(
        folder / "Distributions/Distributions_F1/HR1.csv",
        "coordinate,residual_stress\n0,1\n",
    )
    write(
        folder / "Distributions/Distributions_W1/HR1.csv",
        "coordinate,residual_stress\n0,2\n",
    )
    write(folder / "QP_Coefficients/HR1.csv", HOT_ROLLED_QP)
    git = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(git + ["add", "."], check=True)
    subprocess.run(git + ["commit", "-q", "-m", "base"], check=True)
    return root


def make_delivery(root: Path, old_reference: str = OLD_REFERENCE) -> Path:
    old_row = f'HR1,Hot-rolled wide flange,"{old_reference}",NA\r\n'.encode("utf-8")
    new_row = 'BU1,Built-up wide flange,"“A title” Simões",Q460\r\n'.encode("cp1252")
    write(
        root / "residual_stresses.csv",
        b"id,profile_type,reference,steel-web\r\n" + old_row + new_row,
    )
    write(
        root / "residual_stresses_data_dictionary.csv",
        f"{DICTIONARY_HEADER}\n"
        "id,Identifier,,None,String,HR1,FALSE,Experimental program details\n"
        "profile_type,Type,,None,String,Hot,FALSE,Steel profile\n"
        "reference,Citation,,None,String,X,FALSE,Experimental program details\n"
        "steel-web,Web grade,,None,String,Q460,TRUE,Material properties\n",
        newline="\r\n",
    )
    write(
        root / "Distributions/Distributions_F1/HR1.csv",
        "coordinate,residual_stress\n0,1\n",
        "\r\n",
    )
    write(
        root / "Distributions/Distributions_F1/BU1.csv",
        "Coordinate,Residual Stress\n0,5\n",
        "\r\n",
    )
    write(root / "Distributions/Distributions_W1/HR1.csv", b"")
    write(root / "QP_Coefficients/HR1.csv", HOT_ROLLED_QP)
    write(root / "QP_Coefficients/BU1.csv", BUILT_UP_QP)
    return root


def run(tmp_path: Path, **delivery) -> tuple[int, Path]:
    repo = make_repo(tmp_path / "repo")
    source = make_delivery(tmp_path / "delivery", **delivery)
    code = main([str(source), str(repo), "--base", "HEAD"])
    return code, repo / "residual_stresses"


def test_fix_c1_turns_control_characters_into_quotes():
    assert fix_c1("\u0093a\u0094 1–2 \u0096") == "“a” 1–2 –"


def test_a_delivery_is_cleaned_and_merged(tmp_path: Path):
    code, folder = run(tmp_path)

    assert code == 0
    table = (folder / "residual_stresses.csv").read_text(encoding="utf-8")
    assert table.splitlines() == [
        "id,profile_type,reference,steel_web,data_curation_status",
        "HR1,Hot-rolled wide flange,“The title.” Journal,NA,verified",
        "BU1,Built-up wide flange,“A title” Simões,Q460,verified",
    ]
    dictionary = (folder / "residual_stresses_data_dictionary.csv").read_text()
    assert "\r" not in dictionary
    assert "steel_web,Web grade,,-,String,Q460,True,Material properties" in dictionary
    assert dictionary.rstrip().endswith("Experimental program details")
    assert "data_curation_status,Status" in dictionary
    assert (folder / "Distributions/Distributions_F1/BU1.csv").read_text() == (
        "coordinate,residual_stress\n0,5\n"
    )
    assert (folder / "QP_Coefficients/BU1.csv").read_text() == BUILT_UP_QP


def test_an_empty_file_keeps_the_repo_file(tmp_path: Path):
    code, folder = run(tmp_path)

    assert code == 0
    assert (folder / "Distributions/Distributions_W1/HR1.csv").read_text() == (
        "coordinate,residual_stress\n0,2\n"
    )


def test_a_changed_old_cell_stops_the_import(tmp_path: Path, capsys):
    code, _ = run(tmp_path, old_reference="Another title")

    assert code == 1
    assert "HR1.reference" in capsys.readouterr().err
