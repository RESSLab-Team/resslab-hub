# Flow of uploader.py

`upload_all` is what `make upload-data`, the `/upload` endpoint and the
in-cluster CronJob run. It ends by recomputing the `*_count` flags of every
main table, so specimens without curves show "no test data".

```mermaid
flowchart TD
    A[FastAPI /upload endpoint, make upload-data, CronJob] --> B[upload_all]
    B --> C[get_args_all]

    C --> D{Type = ALL?}
    D -->|Yes| E[Recursive calls for ALL_BRACE, ALL_COLUMN, ..., DICTIONARY, README]
    D -->|No| F[Return specific file tuples]
    E --> G[Collect all tuples]
    F --> G

    G --> H[Expand wildcards]
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
```

# The four uploaders

```mermaid
flowchart TD
    subgraph TableUploader
        T1[Read CSV with headers] --> T2{Headers match DB columns?}
        T2 -->|No| T3[Raise Error]
        T2 -->|Yes| T4[Create DB Session]
        T4 --> T5[For each row: convert types, session.merge]
        T5 --> T6[Delete rows whose id is no longer in the CSV]
        T6 --> T7[Commit]
    end

    subgraph CsvFileUploader
        C1[Parse filename for the parent id] --> C2[Read CSV, validate required columns]
        C2 --> C3[Build plain dict rows, no ORM objects]
        C3 --> C4[Delete the parent's old rows]
        C4 --> C5[One COPY FROM STDIN for the whole file]
        C5 --> C6{Foreign key error?}
        C6 -->|Yes| C7[Roll back, log, skip the file]
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
