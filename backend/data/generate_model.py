import csv
import re
import sys
from typing import Tuple


def get_sqlalchemy_type(type_str: str) -> str:
    """Convert CSV type string to SQLAlchemy type"""
    type_mapping = {
        "Numeric": "Numeric",
        "DecimalFloat": "DecimalFloat",
        "SmallInteger": "SmallInteger",
        "BigInteger": "BigInteger",
        "Integer": "Integer",
        "String": "String",
        "Date": "Date",
        "Boolean": "Boolean",
    }
    return type_mapping.get(type_str, "String")


def get_pydantic_type(type_str: str) -> str:
    """Convert CSV type string to Pydantic type"""
    type_mapping = {
        "Numeric": "float",
        "DecimalFloat": "float",
        "SmallInteger": "int",
        "BigInteger": "int",
        "Integer": "int",
        "String": "str",
        "Date": "date",
        "Boolean": "bool",
    }
    return type_mapping.get(type_str, "str")


def generate_model_from_csv(csv_path: str) -> Tuple[str, str]:
    """Generate both SQLAlchemy and Pydantic model code from CSV"""
    db_code = []
    api_code = []

    with open(csv_path, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            column_name = row["column_name"]
            sqlalchemy_type = get_sqlalchemy_type(row["type"])
            pydantic_type = get_pydantic_type(row["type"])
            nullable = row["nullable"] == "True"

            # Generate database model code
            if column_name == "id":
                db_code.append(f"    {column_name} = Column(String, primary_key=True)")
            else:
                db_code.append(
                    f"    {column_name} = Column("
                    f"{sqlalchemy_type}, nullable={nullable})"
                )

            # Generate API model code
            optional = "Optional[" if nullable else ""
            closing_bracket = "]" if nullable else ""
            api_code.append(
                f"    {column_name}: {optional}{pydantic_type}{closing_bracket}"
            )

    return "\n".join(db_code), "\n".join(api_code)


def update_file(model_path: str, generated_code: str, suffix: str = None) -> None:
    """Update the model file by replacing content between markers"""
    with open(model_path, "r") as f:
        content = f.read()

    start_marker = f"# START_OF_GENERATED_CODE{'_' + suffix if suffix else ''}"
    end_marker = f"# END_OF_GENERATED_CODE{'_' + suffix if suffix else ''}"
    # Define the pattern to match everything between the markers (including markers)
    pattern = f"({start_marker}\n).*?({end_marker})"

    # Replace the content between markers with new generated code
    new_content = re.sub(
        pattern,
        r"\1" + generated_code + r"\n    \2",
        content,
        flags=re.DOTALL,
    )

    # Write the updated content back to the file
    with open(model_path, "w") as f:
        f.write(new_content)


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(
            "Usage: python generate_model.py <csv_file_path> "
            "<db_model_path> <api_model_path> <suffix/model name>"
        )
        sys.exit(1)

    csv_file_path = sys.argv[1]
    db_model_path = sys.argv[2]
    api_model_path = sys.argv[3]
    suffix = sys.argv[4]

    # Generate both model codes
    db_code, api_code = generate_model_from_csv(csv_file_path)

    # Update database model file
    update_file(db_model_path, db_code)

    # Update API model file
    update_file(api_model_path, api_code, suffix)
