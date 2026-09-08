# SEM images

The ductile-fracture specimens can carry Scanning Electron Microscopy images
of their fracture surface. This page says where the raw images live, what the
processing script computes, where the results are stored, and how the app
reads them. The contributor-facing rules (file names, what to send) are in
the data repo, `material/ductile_fracture/README.md`.

## Where things live

| What | Where | Tracked by |
|---|---|---|
| Raw TIFs, one folder per coupon | `resslab-hub-data/material/ductile_fracture/sem/<id>/` | git, in Git LFS (`*.tif`, about 700 files, 1.7 GB) |
| WebP images, dimple JSONs, manifest | `https://enacit4r-cdn.epfl.ch/resslab-hub/sem/<id>/...` | the EPFL enacit4r CDN (an S3 bucket at `s3.epfl.ch`, served under that host) |
| Same, for local dev | `resslab-hub-data/material/ductile_fracture/sem/_webp/<id>/` | nothing, gitignored in the data repo |
| The `has_sem` flag | column of `ductile_fracture.csv`, then the database | the data repo, set by the script |

The app never serves a TIF. It reads the CDN (or the local `_webp` folder)
and shows the SEM section of the drawer only when `has_sem` is `yes`
(`DuctileFractureDetail.vue`).

Today: 36 coupons out of 102 have images.

## File names in the data repo

`<location>_<magnification>[_<surface>].tif` and `global[_<surface>].tif`.
Location is `north`, `south`, `east`, `west` or `middle`; magnification is
250, 500 or 2000. The optional `_2` marks the second fracture surface of a
ruptured bar (Ozden et al. coupons image both halves). A full CNT folder is
`global.tif` plus five locations at three magnifications, 16 files; grooved
plates have no north and south, 10 files. The parser is `parse_filename` in
`backend/data/precompute_sem.py`; a file that does not match is skipped with
a warning.

## The script

`backend/data/precompute_sem.py`, run through the Makefile:

```bash
cd backend
DRY_RUN=1 make precompute-sem     # local only, output in sem/_webp/
make precompute-sem               # same, uploaded to the CDN, has_sem written
```

It needs the `sem` dependency group (`uv run --group sem`: OpenCV headless,
scikit-image, Pillow, exifread, boto3) and `RESSLAB_DATA_DIR`. For each
folder under `sem/`:

1. Every TIF becomes a WebP (quality 85), same name, `global.webp` or
   `<location>_<magnification>.webp`, the second surface under `s2/`.
2. Every non-global image gets its dimples measured. The pixel size comes
   from the TIF's EXIF (tag `0x8546`, the microscope writes it); without it
   the image is converted but not measured, with a warning. The measurement
   is `process_sem` in `backend/data/process_sem_lib.py`, ported from the
   lab's notebook: crop the legend strip at the bottom, median filter, CLAHE,
   threshold, morphological opening, external contours, then the equivalent
   diameter of each contour in mm. The sorted list is written to
   `dimples_<location>_<magnification>.json`, and all images of a surface
   are pooled into `dimples_all.json`.
3. `manifest.json` records what exists: number of surfaces, locations,
   magnifications. The dialog reads it to know which hotspots to draw.
4. Without `DRY_RUN`, every file is uploaded to
   `s3://<BUCKET_NAME>/resslab-hub/sem/<id>/...`, and `has_sem` is set to
   `yes` in `ductile_fracture.csv` for the processed ids (set only, never
   cleared). Commit that CSV change to the data repo and open the pull
   request, the flag reaches the database at the next upload.

The run is idempotent: an unchanged folder produces the same files, and an
upload overwrites the same keys.

### Environment for the upload

| Variable | What |
|---|---|
| `ACCESS_KEY_ID`, `ACCESS_KEY_SECRET` | S3 credentials for the EPFL CDN, from EPFL ops (KeeWeb). |
| `BUCKET_NAME` | the shared enacit4r bucket, same source. Required. |
| `S3_ENDPOINT_URL` | `https://s3.epfl.ch` by default. |
| `CDN_PREFIX` | `resslab-hub` by default. Must match `VITE_SEM_CDN_BASE_URL` in `frontend/.env.production`. |
| `DRY_RUN` | `1` skips the upload and the CSV write. |

The CDN rejects the trailing checksums newer boto3 versions send by default;
the script turns them off in `_make_s3_client`, do not "clean that up".

## Local development

The frontend reads `VITE_SEM_CDN_BASE_URL`. `.env.development` sets it to
`/sem`, which Vite serves from `frontend/public/sem`. Create that symlink
once, it is gitignored (a dangling link inside the Docker build context
would break the production build):

```bash
cd backend && DRY_RUN=1 make precompute-sem
ln -s ../../../resslab-hub-data/material/ductile_fracture/sem/_webp frontend/public/sem
```

With the symlink in place `pnpm run dev` shows the same SEM dialog as
production, from local files. Production builds use `.env.production`, the
real CDN.

## How the app uses it

`frontend/src/utils/sem.ts` builds the URLs (`semGlobalImageUrl`,
`semLocalImageUrl`, `semDimplesUrl`, `semManifestUrl`) and fetches the
manifest. `components/ductile-fracture/sem/`:

- `SemDialog.vue`: the global image with hotspots at the imaged locations
  (positions per specimen type, `CNT_HOTSPOTS` and `GP_HOTSPOTS` in
  `sem.ts`), a surface switch when the manifest says two, and the local
  image at the chosen magnification. A specimen without a manifest (older
  upload) is treated as one surface with the full hotspot set.
- `SemHotspots.vue`: the hotspot overlay.
- `SemCdfChart.vue`: the cumulative distribution of dimple diameters, per
  image or pooled, from the JSON files.

## Adding images for a coupon

1. Put the TIFs in `sem/<id>/` in the data repo with the names above, `id`
   being the coupon's id in `ductile_fracture.csv`. The submission form does
   not take images yet; open a pull request, or send them to a curator.
2. Run `DRY_RUN=1 make precompute-sem` and open the coupon locally to check
   the hotspots and the dimples.
3. Run `make precompute-sem` with the CDN credentials, commit the
   `has_sem` change, open the pull request, merge, run the upload CronJob
   ([backend/README.md](../backend/README.md)).

Nothing else changes: the CDN path is derived from the id, the dialog reads
the manifest.
