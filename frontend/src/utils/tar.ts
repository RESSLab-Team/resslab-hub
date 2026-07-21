/**
 * Minimal POSIX ustar writer.
 *
 * The backend's `/validate` endpoint opens uploads with `tarfile.open(mode="r:gz")`,
 * so a contribution has to reach it as a gzipped tar. Rather than pull in a tar
 * dependency for the handful of single-CSV archives this app builds, we emit the
 * ustar format directly: it is a sequence of 512-byte blocks, one header per entry
 * followed by the padded file body, terminated by two zero blocks.
 */

const BLOCK = 512
const encoder = new TextEncoder()

export interface TarEntry {
  /** Path inside the archive, e.g. `braces/steel_braces.csv`. */
  path: string
  content: string | Uint8Array
}

function writeString(block: Uint8Array, offset: number, value: string, length: number): void {
  const bytes = encoder.encode(value)
  if (bytes.length > length) {
    throw new RangeError(`Value "${value}" exceeds its ${length}-byte tar header field`)
  }
  block.set(bytes, offset)
}

/** Octal, zero-padded, NUL-terminated — the ustar convention for numeric fields. */
function writeOctal(block: Uint8Array, offset: number, value: number, length: number): void {
  writeString(block, offset, value.toString(8).padStart(length - 1, '0'), length)
}

function buildHeader(path: string, size: number, mtimeSeconds: number): Uint8Array {
  const header = new Uint8Array(BLOCK)

  writeString(header, 0, path, 100) // name
  writeOctal(header, 100, 0o644, 8) // mode
  writeOctal(header, 108, 0, 8) // uid
  writeOctal(header, 116, 0, 8) // gid
  writeOctal(header, 124, size, 12) // size
  writeOctal(header, 136, mtimeSeconds, 12) // mtime
  header[156] = 0x30 // typeflag '0' — regular file
  writeString(header, 257, 'ustar', 6) // magic (NUL-terminated)
  writeString(header, 263, '00', 2) // version
  writeString(header, 265, 'root', 32) // uname
  writeString(header, 297, 'root', 32) // gname

  // Checksum is the unsigned byte sum of the header with the checksum field
  // itself treated as eight spaces, written back as six octal digits + NUL + space.
  header.fill(0x20, 148, 156)
  let checksum = 0
  for (const byte of header) checksum += byte
  writeString(header, 148, checksum.toString(8).padStart(6, '0'), 6)
  header[154] = 0
  header[155] = 0x20

  return header
}

/**
 * Build an uncompressed tar archive.
 *
 * Directory entries are omitted deliberately — Python's `tarfile.extractall`
 * creates missing parent directories for nested member paths.
 */
export function buildTar(entries: TarEntry[], mtimeSeconds = 0): Uint8Array {
  const bodies = entries.map((entry) =>
    typeof entry.content === 'string' ? encoder.encode(entry.content) : entry.content
  )
  const size = bodies.reduce(
    (total, body) => total + BLOCK + Math.ceil(body.length / BLOCK) * BLOCK,
    0
  )
  const archive = new Uint8Array(size + BLOCK * 2)

  let offset = 0
  entries.forEach((entry, i) => {
    const body = bodies[i]
    archive.set(buildHeader(entry.path, body.length, mtimeSeconds), offset)
    offset += BLOCK
    archive.set(body, offset)
    offset += Math.ceil(body.length / BLOCK) * BLOCK
  })

  return archive
}

/** Build a gzipped tar as a `File`, ready to hand to the generated API client. */
export async function buildTarGz(entries: TarEntry[], filename: string): Promise<File> {
  const tar = buildTar(entries)
  const gzipped = await new Response(
    new Blob([tar as BlobPart]).stream().pipeThrough(new CompressionStream('gzip'))
  ).blob()
  return new File([gzipped], filename, { type: 'application/gzip' })
}
