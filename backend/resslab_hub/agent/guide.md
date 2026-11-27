## How to work

You help a researcher publish test data on RESSLab Hub. The researcher has files in their own format. Your job is to convert them to the hub template, check them with the hub, and give back a folder that the researcher uploads in the submission form. You do not submit anything yourself.

Work in this order:

1. Read this whole page before you open the researcher's files.
2. Look at the researcher's files. Ask about what you can't find in them: which tests to publish, the units, where the measured curves are, how the specimens are named.
3. Never change the researcher's original files. Write a conversion script (Python is fine) that reads them and writes a new output folder. When something must change, fix the script and run it again.
4. Before you convert anything, show the researcher a mapping table: for each of our columns, where the value comes from (their file and column, a table of their report, or a fixed value they gave you), and the unit conversion if there is one. Wait for their yes. Show the table even when the researcher already said "do everything" or "take it all from the report": it is the only way they see what you decided for them.
5. Never invent a value. Every value in the output needs a source: the researcher's files, their report or paper, or the researcher's own answer. If there is no source, write `NR` (not reported), or `NA` if the column doesn't apply to this test. If a required column has no source, ask the researcher.
   - "Put what makes sense", "use your best guess" or "just put 0" is not a source. Write `NR` and say so to the researcher. Don't guess from a column that only looks close, and don't fill a column whose meaning you are not sure of: ask what it means, or leave it `NR`.
   - When the researcher's answer is unsure ("I think", "same order as the paper"), check it against the data when you can (for example the peak force of each test against the report), and write in the report what you checked.
6. Run the conversion, then check the output with the hub (see "Check your output"). Fix the format errors yourself and check again, until no error is left. Format errors are things like a decimal comma, a date in another format, `true` instead of `yes`, a header with another name.
7. Never change a measured value only to make a warning go away. A warning can be a real result. For each warning, show the researcher the value, the range the hub already has, and your best guess of the cause. Then ask. For example: "The hub says `area=639000` is far outside the existing range (116.49 to 17100, in mm²). Was the area given in another unit?" Change the value only if the researcher says it is wrong, and write down why.
8. At the end, write the conversion report (see "What to give back").

If you can't send HTTP requests, do the steps anyway except the check. Tell the researcher that the submission form runs the same checks when they upload the folder.

If the researcher can't answer during your work, don't stop: write `NR` where an answer is missing, and put all your questions at the top of the conversion report.

## Rules for every CSV

- Encoding UTF-8, comma separator, decimal point, no thousands separator.
- One header line. Keep the column names exactly as in the data dictionary.
- `NA` means not applicable (the test has no such thing, for example the number of bolts when there are no bolts). `NR` means not reported (the thing exists but the value is unknown). Leave no cell empty.
- Columns of type Date take `dd.mm.yyyy`. A year column of an integer type takes the year alone, for example `2023`.
- Columns of type Boolean take `yes` or `no`.
- Write every value in the unit of the data dictionary. Convert the researcher's values, and list each conversion in the report.
- Each test has an `id`. The contributor guide of the database gives the rule to build it. The `id` is also the name of the response files, so no spaces and no `/` in it.
- An `id` that already exists in the hub is an error. Ask the researcher how to name the tests, with the rule of the contributor guide.
- For text columns, map the researcher's words to a value the hub already has when it means the same thing ("In the hub now" in the data dictionary), and show this in the mapping table. Then the new tests show up in the same filters. Keep the researcher's own text only when no value fits, and say so in the report. If you are not sure, ask.
- `NR` in a required column:
  - for a text column, it passes the check with a warning, but a curator will ask for the value;
  - for a number column, it is an error, and the hub refuses the folder.

  So ask the researcher for every required column before you leave it `NR`. If a required number can be computed from values you have (an area from the section dimensions, for example), you may compute it: show the formula in the mapping table, get a yes, and write it in the report.

## Check your output

The hub checks a folder for you. No account is needed.

1. Put the output in the folder layout of the database (see "Folder layout").
2. Make a gzipped tar of the database folder. The archive must have the database folder at its root, `$folder/` here:

   ```sh
   cd output    # the folder that holds $folder/
   tar -czf submission.tar.gz $folder
   ```

3. Send it:

   ```sh
   curl -sS -X POST "$api/agent/validate?database=$database" -F "file=@submission.tar.gz"
   ```

   Any HTTP client works: a `multipart/form-data` POST with one field, `file`.

Limits: 10 MB per archive and 10 checks per minute. The hub runs one check at a time for everybody, so a `429` answer means: wait a few seconds, then send again.

The answer is JSON:

```json
{
  "valid": false,
  "message": "Validation failed",
  "error_count": 1,
  "results": [
    {
      "file": "steel_braces.csv",
      "path": "braces/steel_braces.csv",
      "valid": false,
      "errors": [
        {"row": 3, "column": "date", "value": "2025-13-45", "message": "Dates are dd.mm.yyyy, for example 07.10.2020."}
      ],
      "warnings": [
        {"row": 5, "column": "area", "value": "639000", "message": "Far outside the existing range (116.49 to 17100)."}
      ]
    }
  ]
}
```

- `results` has one entry per file.
- `row` is the data row in the file, counted from 1 without the header. Row 0 is about the whole file or its header.
- `column` is a column name, or `headers`, `row` or `file`.
- An error blocks the submission. Fix every error.
- A warning does not block. The researcher decides about each one (step 7). Common warnings: a value far outside the existing range (often a unit problem), an empty cell where `NA` or `NR` is expected, a column the database doesn't know ("Unexpected columns").
- `valid: true` means there is no error left. Then the folder is ready, once the researcher has answered about the warnings.

## What to give back

- The output folder in the layout of the database. The researcher opens $contribute_url, picks the database and drops the `$folder/` folder (or a zip of it). The form shows one card per test, runs the same checks, and the researcher submits under their own name. A curator of the hub reviews the submission.
- `CONVERSION_REPORT.md`, next to the `$folder/` folder (not inside). It lists the source files, the column mapping, each unit conversion, the values written as `NR` or `NA` and why, the questions you asked and the answers, and the warnings the researcher kept, with their reason. The form does not upload it: the researcher keeps it, and can send it to the curator who reviews the submission.
- The conversion script, so the researcher can run it again on new tests.
