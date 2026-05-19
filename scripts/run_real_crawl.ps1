# scripts/run_real_crawl.ps1
# Kick off the real polite crawl of quotes.toscrape.com that produces
# data/index.json. Runs at the brief's 6 s politeness window between
# requests, so total wall time is around 6-10 minutes for the full site.
# Run this in its own PowerShell window:
#   cd $HOME\comp3011-cw2
#   .\scripts\run_real_crawl.ps1

$ErrorActionPreference = "Stop"

# Activate the project venv so `python` resolves to the right interpreter.
.\.venv\Scripts\Activate.ps1

# Use a single-quoted here-string so PowerShell does not interpret `$`,
# backticks, or `{...}` inside the Python source. Pipe the source via stdin
# to `python -` rather than passing it via `-c "..."` because PowerShell's
# Win32 argv encoding does not escape embedded double-quotes, which would
# turn `print("hi")` into `print(hi)` and crash the script before it starts.
$pythonCode = @'
from src.crawler import Crawler, CrawlerConfig
from src.indexer import InvertedIndex
from src.storage import save_index
import time

print("Starting real crawl with 6s politeness; expect 6-10 minutes for ~60 pages.")
t0 = time.time()
crawler = Crawler(CrawlerConfig())
pages = crawler.crawl()
print(f"Crawled {len(pages)} pages in {(time.time()-t0)/60:.1f} min.")
index = InvertedIndex()
index.build_from_pages(pages)
save_index(index.to_dict())
print(f"Saved index: {index.term_count} terms, {index.document_count} pages.")
'@

$pythonCode | python -
