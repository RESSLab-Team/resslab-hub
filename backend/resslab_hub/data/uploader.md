# Flow of uploader.py

`upload_all` is what `make upload-data`, the `/upload` endpoint and the
in-cluster CronJob run. It uploads only the files whose sha256 differs from
the one in the `uploaded_file` table (`--force` uploads all), and deletes the
rows of the files that left the data repo. It ends by recomputing the
`*_count` flags of every main table, so specimens without curves show "no test
data". The rules (keys, when it removes, when to force) are in
`backend/README.md`, "What a run uploads".

```mermaid
flowchart TD
    A[FastAPI /upload endpoint, make upload-data, CronJob] --> B[upload_all]
    B --> C{Type = ALL?}
    C -->|Yes| D[The nine groups ALL_BRACE, ALL_COLUMN, ...]
    C -->|No| E[One group: the given type]
    D --> G[get_args_all per group, expand wildcards]
    E --> G

    G --> R{ALL or ALL_* group, main CSV present?}
    R -->|Yes| R2[Removed: tracked keys of the group not in the folder]
    R -->|No| H2
    R2 --> H2[cap_series: keep N files per series type when --series-limit N]
    H2 --> H3[Hash each file, compare with uploaded_file]
    H3 -->|same hash, no --force| SK[Skip]
    H3 -->|new or changed| I[Split into primary/subsidiary]
    R2 --> RM[delete_one + drop the hash, one transaction per file]

    I --> J[Primary: main tables]
    I --> K[Subsidiary: measurements, dictionaries, READMEs]

    J --> L[upload_parallel]
    K --> M[upload_parallel, biggest files first]

    L --> N[upload_tracked: get_uploader, upload_one, then save the hash]
    M --> N

    N --> O{get_uploader}
    O -->|Main tables| P[TableUploader]
    O -->|Measurements| Q[CsvFileUploader]
    O -->|*_data_dictionary.csv| DU[DictionaryUploader]
    O -->|README.md| S[ReadmeUploader]

    P --> T[recompute_count_flags, then one summary line per group]
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
        C6 -->|Yes| C7[Roll back and raise: no hash is saved, next run retries]
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
