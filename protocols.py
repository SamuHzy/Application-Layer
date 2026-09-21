"""
protocols.py
Builds simulated application-layer protocol message sequences
(DNS, HTTP, SMTP) for the three dashboard activities: browsing,
mail, and streaming. Message formats follow the shapes described in
RFC 1035 (DNS), RFC 9110/9112 (HTTP/1.1), and RFC 5321 (SMTP) closely
enough for teaching purposes; this is a simulation, not a live network
capture.
"""

import random


def rand_ip(prefix):
    """Build a plausible-looking IPv4 address under a given /16-ish prefix."""
    return f"{prefix}.{random.randint(0, 255)}.{random.randint(0, 255)}"


def rand_txid():
    return f"0x{random.randint(0, 0xFFFF):04x}"


# ---------------------------------------------------------------------------
# Individual message builders
# ---------------------------------------------------------------------------

def dns_query(domain, qtype, t):
    return {
        "dir": "c2s",
        "proto": "DNS",
        "time": t,
        "summary": f"DNS query for {domain} ({qtype} record)",
        "detail": (
            f"Transaction ID: {rand_txid()}\n"
            f"Flags: [[QR=0 (query)]], RD=1 (recursion desired)\n"
            f"Questions: 1\n"
            f"Query: [[{domain}]]  type=[[{qtype}]]  class=IN"
        ),
    }


def dns_response(domain, ip, t):
    return {
        "dir": "s2c",
        "proto": "DNS",
        "time": t,
        "summary": f"DNS response — {domain} resolves to {ip}",
        "detail": (
            "Flags: [[s:QR=1 (response)]], RA=1, RCODE=0 (NOERROR)\n"
            f"Answer: [[s:{domain}]]  A  TTL=300  →  [[s:{ip}]]\n"
            "Additional: 0"
        ),
    }


def dns_mx_query(domain, t):
    return {
        "dir": "c2s",
        "proto": "DNS",
        "time": t,
        "summary": f"DNS query for {domain} (MX record)",
        "detail": (
            f"Query: [[{domain}]]  type=[[MX]]  class=IN\n"
            "Purpose: locate the mail exchanger responsible for this domain"
        ),
    }


def dns_mx_response(domain, mx_host, ip, t):
    return {
        "dir": "s2c",
        "proto": "DNS",
        "time": t,
        "summary": f"DNS response — mail exchanger for {domain}",
        "detail": (
            f"Answer: [[s:{domain}]]  MX  preference=10  exchange=[[s:{mx_host}]]\n"
            f"Additional: [[s:{mx_host}]]  A  →  [[s:{ip}]]"
        ),
    }


def http_get(host, path, t, extra_header=None):
    lines = [
        f"[[GET {path} HTTP/1.1]]",
        f"Host: {host}",
        "User-Agent: Wire-Dashboard/1.0",
        "Accept: */*",
        "Connection: keep-alive",
    ]
    if extra_header:
        lines.append(extra_header)
    return {
        "dir": "c2s",
        "proto": "HTTP",
        "time": t,
        "summary": f"HTTP GET request for {path}",
        "detail": "\n".join(lines),
    }


def http_response(status, status_text, content_type, body_preview, t, size_label=None):
    ok = "s" if status < 400 else ""
    return {
        "dir": "s2c",
        "proto": "HTTP",
        "time": t,
        "summary": f"HTTP {status} {status_text}",
        "detail": (
            f"[[{ok}:HTTP/1.1 {status} {status_text}]]\n"
            f"Content-Type: {content_type}\n"
            f"Content-Length: {size_label or '—'}\n"
            "Connection: keep-alive\n\n"
            f"{body_preview}"
        ),
    }


def smtp_line(text, t):
    return {
        "dir": "c2s",
        "proto": "SMTP",
        "time": t,
        "summary": f"{text.split(' ')[0]} command",
        "detail": f"[[{text}]]",
    }


def smtp_reply(code, text, t):
    return {
        "dir": "s2c",
        "proto": "SMTP",
        "time": t,
        "summary": f"{code} {text}",
        "detail": f"[[s:{code} {text}]]",
    }


# ---------------------------------------------------------------------------
# Full activity sequences
# ---------------------------------------------------------------------------

def build_browsing_sequence(raw_url):
    url = raw_url.replace("https://", "").replace("http://", "")
    if "/" in url:
        host, _, rest = url.partition("/")
        path = "/" + rest if rest else "/"
    else:
        host, path = url, "/"

    ip = rand_ip("93.184")
    t = 0
    seq = []

    seq.append(dns_query(host, "A", t)); t += 18
    seq.append(dns_response(host, ip, t)); t += 6
    seq.append(http_get(host, path, t)); t += 42
    body = f"<!DOCTYPE html>\n<html>\n  <head><title>{host}</title></head>\n  <body>…</body>\n</html>"
    seq.append(http_response(200, "OK", "text/html; charset=utf-8", body, t, "1,284 B")); t += 9

    return seq


def build_mail_sequence(to, subject, body):
    domain = to.split("@")[1] if "@" in to else "example.com"
    mx_host = f"mail.{domain}"
    ip = rand_ip("198.51.100")
    t = 0
    seq = []

    seq.append(dns_mx_query(domain, t)); t += 16
    seq.append(dns_mx_response(domain, mx_host, ip, t)); t += 7
    seq.append({
        "dir": "s2c", "proto": "SMTP", "time": t,
        "summary": "220 service ready",
        "detail": f"[[s:220 {mx_host} ESMTP ready]]",
    }); t += 5
    seq.append(smtp_line("EHLO wire-dashboard.local", t)); t += 4
    seq.append(smtp_reply("250", "Hello, pleased to meet you", t)); t += 4
    seq.append(smtp_line(f"MAIL FROM:<[email protected]>", t)); t += 4
    seq.append(smtp_reply("250", "OK", t)); t += 4
    seq.append(smtp_line(f"RCPT TO:<{to}>", t)); t += 4
    seq.append(smtp_reply("250", "OK", t)); t += 4
    seq.append(smtp_line("DATA", t)); t += 3
    seq.append(smtp_reply("354", "Start mail input; end with <CRLF>.<CRLF>", t)); t += 3
    seq.append({
        "dir": "c2s", "proto": "SMTP", "time": t,
        "summary": "message headers and body",
        "detail": (
            f"Subject: [[{subject}]]\n"
            "From: [email protected]\n"
            f"To: {to}\n\n"
            f"{body}\n[[.]]"
        ),
    }); t += 10
    seq.append(smtp_reply("250", "OK: message queued for delivery", t)); t += 3
    seq.append(smtp_line("QUIT", t)); t += 2
    seq.append(smtp_reply("221", "Service closing transmission channel", t))

    return seq


QUALITY_BITRATE = {"1080p": "5.0 Mbps", "720p": "2.8 Mbps", "480p": "1.2 Mbps"}
QUALITY_BANDWIDTH = {"1080p": 5_000_000, "720p": 2_800_000, "480p": 1_200_000}
QUALITY_RESOLUTION = {"1080p": "1920x1080", "720p": "1280x720", "480p": "854x480"}
QUALITY_SEGMENT_BYTES = {"1080p": "2,431,890 B", "720p": "1,318,220 B", "480p": "602,140 B"}
QUALITY_SEGMENT_MB = {"1080p": "2.4", "720p": "1.3", "480p": "0.6"}


def build_streaming_sequence(raw_url, quality):
    host = raw_url.replace("https://", "").replace("http://", "")
    ip = rand_ip("203.0.113")
    t = 0
    seq = []

    seq.append(dns_query(host, "A", t)); t += 15
    seq.append(dns_response(host, ip, t)); t += 6
    seq.append(http_get(host, "/manifest.m3u8", t)); t += 30

    manifest_body = (
        "#EXTM3U\n#EXT-X-VERSION:3\n"
        f"#EXT-X-STREAM-INF:BANDWIDTH={QUALITY_BANDWIDTH[quality]},"
        f"RESOLUTION={QUALITY_RESOLUTION[quality]}\n"
        f"[[{quality}/index.m3u8]]"
    )
    seq.append(http_response(200, "OK", "application/vnd.apple.mpegurl", manifest_body, t, "212 B")); t += 8

    for i in range(1, 4):
        seg = f"segment{str(i).zfill(3)}.ts"
        seq.append(http_get(host, f"/{quality}/{seg}", t, "Range: bytes=0-")); t += 26
        body = f"[binary media segment, ~{QUALITY_SEGMENT_MB[quality]} MB — {QUALITY_BITRATE[quality]}]"
        seq.append(http_response(200, "OK", "video/MP2T", body, t, QUALITY_SEGMENT_BYTES[quality])); t += 6

    return seq
