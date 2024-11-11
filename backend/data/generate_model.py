import csv
import re
import sys


def get_sqlalchemy_type(type_str: str) -> str:
    """Convert CSV type string to SQLAlchemy type"""
    type_mapping = {
        "SmallInteger": "SmallInteger",
        "String": "String",
        "DecimalFloat": "DecimalFloat",
        "Date": "Date",
    }
    return type_mapping.get(type_str, "String")


def generate_model_from_csv(csv_path: str) -> str:
    """Generate SQLAlchemy model code from CSV schema definition"""
    code = []
    with open(csv_path, "r") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            column_name = row["column_name"]
            sqlalchemy_type = get_sqlalchemy_type(row["type"])
            nullable = row["nullable"] == "True"

            if column_name == "id":
                code.append(f"    {column_name} = Column(String, primary_key=True)")
            else:
                code.append(
                    f"    {column_name} = Column("
                    f"{sqlalchemy_type}, nullable={nullable})"
                )

    return "\n".join(code)


def update_model_file(model_path: str, generated_code: str) -> None:
    """Update the model file by replacing content between markers"""
    with open(model_path, "r") as f:
        content = f.read()

    # Define the pattern to match everything between the markers (including markers)
    pattern = r"(# START_OF_GENERATED_CODE\n).*?(# END_OF_GENERATED_CODE)"

    # Replace the content between markers with new generated code
    new_content = re.sub(
        pattern,
        r"\1" + generated_code + "\n    # END_OF_GENERATED_CODE",
        content,
        flags=re.DOTALL,
    )

    # Write the updated content back to the file
    with open(model_path, "w") as f:
        f.write(new_content)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_model.py <csv_file_path> <model_file_path>")
        sys.exit(1)

    csv_file_path = sys.argv[1]
    model_file_path = sys.argv[2]

    # Generate the new code
    generated_code = generate_model_from_csv(csv_file_path)

    # Update the model file
    update_model_file(model_file_path, generated_code)
