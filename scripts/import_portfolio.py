"""Import a verified public snapshot once, then validate this repo's own pages."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha1
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import urlopen
import json
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://yh-pa-rk.github.io/research-portfolio/'
PREFIX = '/portfolio/'


def download(item):
    relative = item['path']
    assert not relative.startswith('/') and '..' not in Path(relative).parts
    for attempt in range(3):
        try:
            with urlopen(SOURCE + quote(relative), timeout=60) as response:
                data = response.read()
            digest = sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if digest != item['sha']:
                raise ValueError('Snapshot hash mismatch: ' + relative)
            target = ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            return relative
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if not value:
                continue
            values = [value]
            if key == 'srcset':
                values = [part.strip().split()[0] for part in value.split(',') if part.strip()]
            elif key not in ('href', 'src', 'poster', 'data-src'):
                continue
            for value in values:
                if value.startswith('/'):
                    self.paths.add(urlsplit(value).path)


def validate():
    count = 0
    for relative in ('index.html', 'activities/index.html', 'cv/index.html'):
        text = (ROOT / relative).read_text()
        assert '/research-portfolio/' not in text, relative
        parser = Links()
        parser.feed(text)
        for path in parser.paths:
            assert path.startswith(PREFIX), (relative, path)
            target = ROOT / path[len(PREFIX):]
            if path.endswith('/'):
                target /= 'index.html'
            assert target.is_file(), (relative, path)
            count += 1
        for route in (PREFIX, PREFIX+'activities/', PREFIX+'cv/'):
            assert route in text, (relative, route)
    print('Validated', count, 'local page, image, style, script and PDF references.')


def main():
    if not (ROOT / 'index.html').exists():
        manifest = json.loads((ROOT / 'import-manifest.json').read_text())
        with ThreadPoolExecutor(max_workers=8) as pool:
            copied = list(pool.map(download, manifest))
        for relative in ('index.html', 'activities/index.html', 'cv/index.html'):
            path = ROOT / relative
            path.write_text(path.read_text().replace('/research-portfolio/', PREFIX))

        import fitz
        pdf = ROOT / 'assets/pdf/yeonghun-park-cv.pdf'
        document = fitz.open(pdf)
        text_before = [page.get_text() for page in document]
        pixels_before = [page.get_pixmap().samples for page in document]
        changed = 0
        for page in document:
            for link in page.get_links():
                if link.get('uri') == SOURCE:
                    link['uri'] = 'https://yh-pa-rk.github.io' + PREFIX
                    page.update_link(link)
                    changed += 1
        assert changed == 1
        temporary = pdf.with_suffix('.new.pdf')
        document.save(temporary, garbage=4, deflate=True)
        document.close()
        with fitz.open(temporary) as check:
            assert [page.get_text() for page in check] == text_before
            assert [page.get_pixmap().samples for page in check] == pixels_before
        temporary.replace(pdf)
        (ROOT / '.nojekyll').touch()
        print('Imported', len(copied), 'verified files. PDF appearance and text are unchanged.')
    else:
        print('Using the independent files already committed to this repository.')
    validate()
    output = ROOT / '_site'
    if output.exists():
        shutil.rmtree(output)
    output.mkdir()
    for relative in ('index.html', 'activities', 'cv', 'assets', '.nojekyll'):
        source = ROOT / relative
        destination = output / relative
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)


if __name__ == '__main__':
    main()
