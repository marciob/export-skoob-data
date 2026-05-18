# export-skoob-data

Export your entire [Skoob](https://www.skoob.com.br) library to clean JSON —
every shelf, every book, de-duplicated, with no third-party services and
**zero dependencies** (Python 3.8+ standard library only).

Skoob has no official export. This talks to the same private API the Skoob
web app uses (`prd-api.skoob.com.br`), read-only (`GET` only — it never
modifies your account).

## What you get

```
output/
  books.json                 every unique book, de-duplicated, each tagged
                              with the shelves it belongs to
  raw/{type}__{filter}.json   one file per shelf, exactly as the API returns
```

Each book includes: `title`, `author`, `publisher`, `year`, `pages`,
`cover_filename`, `slug`, `status`, `progress`, `finished_at`, `book_id`,
`edition_id`, plus `shelves` (which shelves it's on), `bookshelf_types`,
and `in_library`.

> Note: the bookshelf API does **not** return ISBN, synopsis, or genres —
> those live on a separate per-book endpoint and are intentionally out of
> scope here to keep this tool fast and lightweight.

## Requirements

- Python 3.8 or newer. Nothing else — no `pip install`.

## Getting your Skoob token

Skoob authenticates API calls with a JWT that lives in an **HttpOnly
cookie**, so it can't be read from storage — you have to grab it from a
real request your browser makes. It expires roughly **15 days** after
issue, so you'll repeat this when it stops working.

1. Open <https://www.skoob.com.br/> and **log in**.
2. Open DevTools → **Console** (`F12`, or `Cmd+Option+J` / `Ctrl+Shift+J`).
3. Paste the entire contents of [`get-jwt.js`](./get-jwt.js) and press Enter.
   You'll see `Interceptor armed. Now click any shelf in the sidebar.`
4. **Click any shelf** in the left sidebar (e.g. *Lido*, *Lendo*,
   *Quero ler*), or open your bookshelf page.
5. The console prints `SKOOB JWT: eyJ...` and copies it to your clipboard.

The snippet is read-only: it just observes one outgoing request to read
the `Authorization` header, then removes itself. It never sends, stores,
or transmits anything.

Your `user_id` is read automatically from the token — you don't need to
find it yourself.

## Usage

```bash
git clone <your-fork-url>
cd export-skoob-data

cp .env.example .env
# open .env and paste your token after SKOOB_JWT=

python3 export_skoob.py
```

Or without a file:

```bash
SKOOB_JWT="eyJ..." python3 export_skoob.py
```

Expected output:

```
Token OK — user_id 6xxxxxxxxxxxxxxxxxxxxxxx, ~12.4 day(s) until expiry.
  book     all            total=1060  got=1060
  book     read           total=137   got=137
  ...
Done. 1062 unique books.
  -> output/books.json
  -> output/raw/  (one file per shelf)
```

## Privacy & safety

- **Your token and your exported data are never committed.** `.env` and
  `output/` are git-ignored. Only the code is tracked.
- Read-only: the tool and the console snippet only issue `GET` requests.
- The token grants access to your account — treat it like a password.
  Don't paste it into issues, logs, or screenshots. If you ever leak it,
  log out of Skoob (or wait ≤15 days) to invalidate it.

## How it works

- Iterates every `bookshelf_type` Skoob accepts (`book`, `magazine`) and
  every shelf `filter`, paginating each to completion.
- The API's `total_items` is authoritative; the tool paginates until a
  short page signals the end, then verifies the collected count.
- `filter=all` is the master library list; shelves are **not** mutually
  exclusive (a book can be in `read`, `rated`, and `owned` at once), so
  membership is recorded per shelf and `all` is tracked as `in_library`.

## Limitations

- Token expires (~15 days) — re-grab it when you get an auth error.
- No ISBN/synopsis/genres (separate endpoint, out of scope here).
- User-created custom shelves/tags are not exposed by Skoob's API; only
  the built-in shelves are exported.
- Unofficial API: Skoob may change or restrict it at any time.

## Disclaimer

Independent project, not affiliated with or endorsed by Skoob. Intended
for exporting **your own** data. Use responsibly and at your own risk.

## License

MIT — see [LICENSE](./LICENSE).
