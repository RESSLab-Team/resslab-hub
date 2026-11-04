# Flow of uploader.py

`upload_all` is what `make upload-data`, the `/upload` endpoint and the
in-cluster CronJob run. It ends by recomputing the `*_count` flags of every
main table, so specimens without curves show "no test data". It returns an
`UploadReport`: the messages of the files that went in, and the paths of the
ones that failed. A failed file does not stop the others. `main()` exits 1 and
`/upload` answers 422 when the list is not empty.

```mermaid
flowchart TD
    A[FastAPI /upload endpoint, make upload-data, CronJob] --> B[upload_all]
    B --> C[get_args_all]

    C --> D{Type = ALL?}
    D -->|Yes| E[Recursive calls for ALL_BRACE, ALL_COLUMN, ..., DICTIONARY, README]
    D -->|No| F[Return specific file tuples]
    E --> G[Collect all tuples]
    F --> G

    G --> R0{--rebuild?}
    R0 -->|Yes| R1{Every main CSV there?}
    R1 -->|No| R2[Raise, nothing written]
    R1 -->|Yes| R3[TRUNCATE the main tables of the run CASCADE]
    R3 --> H
    R0 -->|No| H[Expand wildcards]
    H --> H2[cap_series: keep N files per series type when --series-limit N]
    H2 --> I[Split into primary/subsidiary]

    I --> J[Primary: main tables, dictionaries, READMEs]
    I --> K[Subsidiary: measurement files]

    J --> L[upload_parallel]
    K --> M[upload_parallel, biggest files first]

    L --> N[upload_one]
    M --> N

    N --> O{Select Uploader}
    O -->|Main tables| P[TableUploader]
    O -->|Measurements| Q[CsvFileUploader]
    O -->|*_data_dictionary.csv| R[DictionaryUploader]
    O -->|README.md| S[ReadmeUploader]

    P --> T[recompute_count_flags]
    Q --> T
    T --> U[Log a summary and the failed paths, return UploadReport]
```

# The four uploaders

```mermaid
flowchart TD
    subgraph TableUploader
        T1[Read CSV with headers] --> T2{Headers match DB columns?}
        T2 -->|No| T3[Raise Error]
        T2 -->|Yes| T4[Create DB Session]
        T4 --> T5[For each row: convert types, session.merge]
        T5 --> T6[Delete rows whose id is no longer in the CSV, their curves first]
        T6 --> T7[Commit]
    end

    subgraph CsvFileUploader
        C1[Parse filename for the parent id] --> C2[Read CSV, validate required columns]
        C2 --> C3[Build plain dict rows, no ORM objects]
        C3 --> C4[Delete the parent's old rows]
        C4 --> C5[One COPY FROM STDIN for the whole file]
        C5 --> C6{Foreign key error?}
        C6 -->|Yes| C7[Roll back, raise: upload_checked logs it and marks the file failed]
        C6 -->|No| C8[Commit]
    end

    subgraph DictionaryUploader
        D1[Read *_data_dictionary.csv] --> D2[Replace the rows of that database in dictionary_column, group included]
    end

    subgraph ReadmeUploader
        R1[Read the folder README.md] --> R2[Replace the row of that database in database_readme]
    end
```

The perf notes behind `COPY` and the biggest-first scheduling are in
`docs/modernization-followups.md`.
