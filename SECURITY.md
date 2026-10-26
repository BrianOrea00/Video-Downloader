# Security Policy

Video Downloader runs entirely on your machine. It has no server, no telemetry
and no analytics; the only network traffic is the requests `yt-dlp` makes to the
site you ask it to download from, plus PyPI if you update the engine.

That said, it reads browser cookies when you enable that option and it writes
into your home directory, so security reports are welcome.

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | yes       |
| < 1.0   | no        |

Only the latest release on the
[releases page](https://github.com/BrianOrea00/Video-Downloader/releases) receives
fixes.

## Reporting a vulnerability

Use GitHub's private reporting:

<https://github.com/BrianOrea00/Video-Downloader/security/advisories/new>

Please do not open a public issue for a security problem. Include the version,
your platform, and the smallest set of steps that reproduces it. You can expect
an initial reply within seven days.

## What counts as a security issue

- Cookie or credential exposure through logs, settings, thumbnails or the UI.
- Command injection or arbitrary file write caused by a crafted URL, filename,
  media tag or thumbnail.
- Path traversal in the download folder, thumbnail cache or file opening logic.
- An update path that would install something not verified against the digest
  published by PyPI.
- Non-consensual clipboard reading, or reading it when the setting is off.

## What does not count

- The remote site refusing, rate-limiting or blocking downloads.
- A downloaded file being malicious in itself; that is the source site's content.
- Antivirus or SmartScreen warnings on an unsigned build, which are expected
  until releases are code-signed.

## Local data and logs

- Settings, queue, history and thumbnails live under one per-user data directory
  (see Settings → About for the exact path), never beside the binary.
- `settings.json` stores the cookie file path and browser name. Those values are
  never logged.
- `app.log` passes through a redaction filter: URLs become `host#<sha256 prefix>`
  and the home directory becomes `~`. Traceback text attached to an unhandled
  exception is not rewritten, so read a log before sharing it.
- Clearing history removes duplicate-detection records only; downloaded files
  stay on disk.

## Updates

The application itself does not self-update: new versions are published as
releases. Only the download engine can be refreshed from Settings → Download
Engine, and that path is deliberately narrow:

- the wheel comes from `https://pypi.org/pypi/yt-dlp/json` for the version that
  response advertises;
- the SHA256 digest from the same response must match the downloaded bytes, or
  nothing is unpacked;
- the archive is unpacked into `<data>/engine/<version>/` and checked to contain
  only the `yt_dlp` package, with no absolute or `..` paths;
- `current.json` is replaced atomically, and a version that fails to import is
  discarded at startup in favour of the bundled copy.
