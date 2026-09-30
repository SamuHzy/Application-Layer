"""
protocols.py
Builds simulated application-layer (L7: DNS, HTTP, SMTP) and
transport-layer (L4: UDP, TCP) protocol message sequences for the three
dashboard activities: browsing, mail, and streaming. Message formats
follow the shapes described in RFC 768 (UDP), RFC 9293 (TCP), RFC 1035
(DNS), RFC 9110/9112 (HTTP/1.1), and RFC 5321 (SMTP) closely enough for
teaching purposes; this is a simulation, not a live network capture.
"""

import random


def rand_ip(prefix):
    """Build a plausible-looking IPv4 address under a given /16-ish prefix."""
    return f"{prefix}.{random.randint(0, 255)}.{random.randint(0, 255)}"


def rand_txid():
    return f"0x{random.randint(0, 0xFFFF):04x}"


def rand_ephemeral_port():
    return random.randint(49152, 65535)


# ---------------------------------------------------------------------------
# Transport-Layer (L4: UDP & TCP) message builders
# ---------------------------------------------------------------------------

def udp_datagram(dir_, src_port, dst_port, length, purpose, t):
    em = "s:" if dir_ == "s2c" else ""
    service = "domain (DNS)" if (src_port == 53 or dst_port == 53) else "UDP"
    return {
        "dir": dir_,
        "layer": "L4",
        "proto": "UDP",
        "time": t,
        "summary": f"UDP {src_port} → {dst_port} ({purpose}, Len={length} B)",
        "detail": (
            f"Src Port: [[{em}{src_port}]]  →  Dst Port: [[{em}{dst_port}]] ({service})\n"
            f"Length: [[{em}{length} B]]  Checksum: {rand_txid()} (verified)\n"
            "Transport: connectionless UDP (RFC 768) — no handshake or teardown"
        ),
    }


def tcp_syn(c_port, s_port, seq, win, t):
    return {
        "dir": "c2s",
        "layer": "L4",
        "proto": "TCP",
        "time": t,
        "summary": f"TCP [SYN] {c_port} → {s_port} (Seq={seq}, Win={win})",
        "detail": (
            f"Src Port: [[{c_port}]]  →  Dst Port: [[{s_port}]]\n"
            "Flags: [[SYN]] (0x002) — initiate 3-way handshake\n"
            f"Seq: [[{seq}]]  Ack: 0  Window: [[{win}]]  MSS: 1460 B"
        ),
    }


def tcp_syn_ack(s_port, c_port, seq, ack, win, t):
    return {
        "dir": "s2c",
        "layer": "L4",
        "proto": "TCP",
        "time": t,
        "summary": f"TCP [SYN, ACK] {s_port} → {c_port} (Seq={seq}, Ack={ack}, Win={win})",
        "detail": (
            f"Src Port: [[s:{s_port}]]  →  Dst Port: [[s:{c_port}]]\n"
            "Flags: [[s:SYN, ACK]] (0x012) — acknowledge SYN & synchronize ISN\n"
            f"Seq: [[s:{seq}]]  Ack: [[s:{ack}]]  Window: [[s:{win}]]  MSS: 1460 B"
        ),
    }


def tcp_ack(dir_, src_port, dst_port, seq, ack, win, note, t):
    em = "s:" if dir_ == "s2c" else ""
    return {
        "dir": dir_,
        "layer": "L4",
        "proto": "TCP",
        "time": t,
        "summary": f"TCP [ACK] {src_port} → {dst_port} (Seq={seq}, Ack={ack}, Win={win})",
        "detail": (
            f"Src Port: [[{em}{src_port}]]  →  Dst Port: [[{em}{dst_port}]]\n"
            f"Flags: [[{em}ACK]] (0x010) — {note}\n"
            f"Seq: [[{em}{seq}]]  Ack: [[{em}{ack}]]  Len: 0 B  Window: [[{em}{win}]]"
        ),
    }


def tcp_psh_ack(dir_, src_port, dst_port, seq, ack, length, win, label, t):
    em = "s:" if dir_ == "s2c" else ""
    return {
        "dir": dir_,
        "layer": "L4",
        "proto": "TCP",
        "time": t,
        "summary": f"TCP [PSH, ACK] {src_port} → {dst_port} (Seq={seq}, Ack={ack}, Len={length} B)",
        "detail": (
            f"Src Port: [[{em}{src_port}]]  →  Dst Port: [[{em}{dst_port}]]\n"
            f"Flags: [[{em}PSH, ACK]] (0x018) — push L7 payload ({label})\n"
            f"Seq: [[{em}{seq}]]  Ack: [[{em}{ack}]]  Len: [[{em}{length} B]]  Window: [[{em}{win}]]\n"
            f"Next Expected Seq: {seq + length}"
        ),
    }


def tcp_fin_ack(dir_, src_port, dst_port, seq, ack, win, note, t):
    em = "s:" if dir_ == "s2c" else ""
    return {
        "dir": dir_,
        "layer": "L4",
        "proto": "TCP",
        "time": t,
        "summary": f"TCP [FIN, ACK] {src_port} → {dst_port} (Seq={seq}, Ack={ack}, Win={win})",
        "detail": (
            f"Src Port: [[{em}{src_port}]]  →  Dst Port: [[{em}{dst_port}]]\n"
            f"Flags: [[{em}FIN, ACK]] (0x011) — {note}\n"
            f"Seq: [[{em}{seq}]]  Ack: [[{em}{ack}]]  Len: 0 B  Window: [[{em}{win}]]"
        ),
    }


# ---------------------------------------------------------------------------
# Application-Layer (L7: DNS, HTTP, SMTP) message builders
# ---------------------------------------------------------------------------

def dns_query(domain, qtype, t):
    return {
        "dir": "c2s",
        "layer": "L7",
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
        "layer": "L7",
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
        "layer": "L7",
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
        "layer": "L7",
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
        "layer": "L7",
        "proto": "HTTP",
        "time": t,
        "summary": f"HTTP GET request for {path}",
        "detail": "\n".join(lines),
    }


def http_response(status, status_text, content_type, body_preview, t, size_label=None):
    ok = "s" if status < 400 else ""
    return {
        "dir": "s2c",
        "layer": "L7",
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
        "layer": "L7",
        "proto": "SMTP",
        "time": t,
        "summary": f"{text.split(' ')[0]} command",
        "detail": f"[[{text}]]",
    }


def smtp_reply(code, text, t):
    return {
        "dir": "s2c",
        "layer": "L7",
        "proto": "SMTP",
        "time": t,
        "summary": f"{code} {text}",
        "detail": f"[[s:{code} {text}]]",
    }


# ---------------------------------------------------------------------------
# Full activity sequences (L4 Transport + L7 Application)
# ---------------------------------------------------------------------------

def build_browsing_sequence(raw_url):
    url = raw_url.replace("https://", "").replace("http://", "")
    if "/" in url:
        host, _, rest = url.partition("/")
        path = "/" + rest if rest else "/"
    else:
        host, path = url, "/"

    ip = rand_ip("93.184")
    dns_port = rand_ephemeral_port()
    c_port = rand_ephemeral_port()
    s_port = 80
    c_win = 65535
    s_win = 64240

    t = 0
    seq = []

    # 1. DNS over UDP (:53)
    q_len = 28 + len(host)
    seq.append(udp_datagram("c2s", dns_port, 53, q_len, f"DNS A query for {host}", t)); t += 1
    seq.append(dns_query(host, "A", t)); t += 17
    r_len = q_len + 16
    seq.append(udp_datagram("s2c", 53, dns_port, r_len, f"DNS A response ({ip})", t)); t += 1
    seq.append(dns_response(host, ip, t)); t += 5

    # 2. TCP 3-Way Handshake (:80)
    c_seq = 0
    s_seq = 0
    seq.append(tcp_syn(c_port, s_port, c_seq, c_win, t)); t += 12
    c_seq = 1
    seq.append(tcp_syn_ack(s_port, c_port, s_seq, c_seq, s_win, t)); t += 12
    s_seq = 1
    seq.append(tcp_ack("c2s", c_port, s_port, c_seq, s_seq, c_win, "3-way handshake complete — connection ESTABLISHED", t)); t += 4

    # 3. HTTP GET request & 200 OK response over TCP
    req_len = 112 + len(host) + len(path)
    seq.append(tcp_psh_ack("c2s", c_port, s_port, c_seq, s_seq, req_len, c_win, f"HTTP GET {path}", t)); t += 1
    seq.append(http_get(host, path, t)); t += 38
    c_seq += req_len

    resp_len = 1284
    seq.append(tcp_psh_ack("s2c", s_port, c_port, s_seq, c_seq, resp_len, s_win, "HTTP/1.1 200 OK + HTML body", t)); t += 1
    body = f"<!DOCTYPE html>\n<html>\n  <head><title>{host}</title></head>\n  <body>…</body>\n</html>"
    seq.append(http_response(200, "OK", "text/html; charset=utf-8", body, t, "1,284 B")); t += 6
    s_seq += resp_len

    seq.append(tcp_ack("c2s", c_port, s_port, c_seq, s_seq, c_win, "acknowledge HTTP 200 OK payload", t)); t += 5

    # 4. TCP Connection Teardown (FIN-ACK)
    seq.append(tcp_fin_ack("c2s", c_port, s_port, c_seq, s_seq, c_win, "client initiates active close (FIN_WAIT_1)", t)); t += 10
    c_seq += 1
    seq.append(tcp_fin_ack("s2c", s_port, c_port, s_seq, c_seq, s_win, "server confirms teardown & closes (LAST_ACK)", t)); t += 10
    s_seq += 1
    seq.append(tcp_ack("c2s", c_port, s_port, c_seq, s_seq, c_win, "final ACK — connection CLOSED", t))

    return seq


def build_mail_sequence(to, subject, body):
    domain = to.split("@")[1] if "@" in to else "example.com"
    mx_host = f"mail.{domain}"
    ip = rand_ip("198.51.100")
    dns_port = rand_ephemeral_port()
    c_port = rand_ephemeral_port()
    s_port = 25
    c_win = 65535
    s_win = 64240

    t = 0
    seq = []

    # 1. DNS MX lookup over UDP (:53)
    q_len = 28 + len(domain)
    seq.append(udp_datagram("c2s", dns_port, 53, q_len, f"DNS MX query for {domain}", t)); t += 1
    seq.append(dns_mx_query(domain, t)); t += 15
    r_len = q_len + 32
    seq.append(udp_datagram("s2c", 53, dns_port, r_len, f"DNS MX response ({mx_host})", t)); t += 1
    seq.append(dns_mx_response(domain, mx_host, ip, t)); t += 6

    # 2. TCP 3-Way Handshake (:25)
    c_seq = 0
    s_seq = 0
    seq.append(tcp_syn(c_port, s_port, c_seq, c_win, t)); t += 11
    c_seq = 1
    seq.append(tcp_syn_ack(s_port, c_port, s_seq, c_seq, s_win, t)); t += 11
    s_seq = 1
    seq.append(tcp_ack("c2s", c_port, s_port, c_seq, s_seq, c_win, "3-way handshake complete — SMTP channel ESTABLISHED", t)); t += 4

    def send_c2s_smtp(cmd_text, label, delay):
        nonlocal c_seq, t
        length = len(cmd_text) + 2
        seq.append(tcp_psh_ack("c2s", c_port, s_port, c_seq, s_seq, length, c_win, label, t)); t += 1
        seq.append(smtp_line(cmd_text, t)); t += delay
        c_seq += length

    def send_s2c_smtp(code, reply_text, delay):
        nonlocal s_seq, t
        length = len(f"{code} {reply_text}") + 2
        seq.append(tcp_psh_ack("s2c", s_port, c_port, s_seq, c_seq, length, s_win, f"SMTP {code}", t)); t += 1
        seq.append(smtp_reply(code, reply_text, t)); t += delay
        s_seq += length

    # 3. SMTP session over TCP
    banner = f"220 {mx_host} ESMTP ready"
    banner_len = len(banner) + 2
    seq.append(tcp_psh_ack("s2c", s_port, c_port, s_seq, c_seq, banner_len, s_win, "SMTP 220 greeting", t)); t += 1
    seq.append({
        "dir": "s2c", "layer": "L7", "proto": "SMTP", "time": t,
        "summary": "220 service ready",
        "detail": f"[[s:{banner}]]",
    }); t += 4
    s_seq += banner_len

    send_c2s_smtp("EHLO wire-dashboard.local", "SMTP EHLO", 4)
    send_s2c_smtp("250", "Hello, pleased to meet you", 4)
    send_c2s_smtp("MAIL FROM:<[email protected]>", "SMTP MAIL FROM", 4)
    send_s2c_smtp("250", "OK", 4)
    send_c2s_smtp(f"RCPT TO:<{to}>", "SMTP RCPT TO", 4)
    send_s2c_smtp("250", "OK", 4)
    send_c2s_smtp("DATA", "SMTP DATA", 3)
    send_s2c_smtp("354", "Start mail input; end with <CRLF>.<CRLF>", 3)

    msg_payload = f"Subject: {subject}\r\nFrom: [email protected]\r\nTo: {to}\r\n\r\n{body}\r\n.\r\n"
    msg_len = len(msg_payload)
    seq.append(tcp_psh_ack("c2s", c_port, s_port, c_seq, s_seq, msg_len, c_win, "SMTP message headers & body", t)); t += 1
    seq.append({
        "dir": "c2s", "layer": "L7", "proto": "SMTP", "time": t,
        "summary": "message headers and body",
        "detail": (
            f"Subject: [[{subject}]]\n"
            "From: [email protected]\n"
            f"To: {to}\n\n"
            f"{body}\n[[.]]"
        ),
    }); t += 9
    c_seq += msg_len

    send_s2c_smtp("250", "OK: message queued for delivery", 3)
    send_c2s_smtp("QUIT", "SMTP QUIT", 2)
    send_s2c_smtp("221", "Service closing transmission channel", 3)

    # 4. TCP Connection Teardown (FIN-ACK)
    seq.append(tcp_fin_ack("s2c", s_port, c_port, s_seq, c_seq, s_win, "server closes transmission channel (FIN, ACK)", t)); t += 8
    s_seq += 1
    seq.append(tcp_fin_ack("c2s", c_port, s_port, c_seq, s_seq, c_win, "client acknowledges & sends FIN", t)); t += 8
    c_seq += 1
    seq.append(tcp_ack("s2c", s_port, c_port, s_seq, c_seq, s_win, "final ACK — SMTP TCP connection CLOSED", t))

    return seq


QUALITY_BITRATE = {"1080p": "5.0 Mbps", "720p": "2.8 Mbps", "480p": "1.2 Mbps"}
QUALITY_BANDWIDTH = {"1080p": 5_000_000, "720p": 2_800_000, "480p": 1_200_000}
QUALITY_RESOLUTION = {"1080p": "1920x1080", "720p": "1280x720", "480p": "854x480"}
QUALITY_SEGMENT_BYTES = {"1080p": "2,431,890 B", "720p": "1,318,220 B", "480p": "602,140 B"}
QUALITY_SEGMENT_INT = {"1080p": 2_431_890, "720p": 1_318_220, "480p": 602_140}
QUALITY_SEGMENT_MB = {"1080p": "2.4", "720p": "1.3", "480p": "0.6"}


def build_streaming_sequence(raw_url, quality):
    host = raw_url.replace("https://", "").replace("http://", "")
    ip = rand_ip("203.0.113")
    dns_port = rand_ephemeral_port()
    c_port = rand_ephemeral_port()
    s_port = 80
    c_win = 65535
    s_win = 64240

    t = 0
    seq = []

    # 1. DNS Resolution over UDP (:53)
    q_len = 28 + len(host)
    seq.append(udp_datagram("c2s", dns_port, 53, q_len, f"DNS A query for {host}", t)); t += 1
    seq.append(dns_query(host, "A", t)); t += 14
    r_len = q_len + 16
    seq.append(udp_datagram("s2c", 53, dns_port, r_len, f"DNS A response ({ip})", t)); t += 1
    seq.append(dns_response(host, ip, t)); t += 5

    # 2. TCP 3-Way Handshake (:80)
    c_seq = 0
    s_seq = 0
    seq.append(tcp_syn(c_port, s_port, c_seq, c_win, t)); t += 10
    c_seq = 1
    seq.append(tcp_syn_ack(s_port, c_port, s_seq, c_seq, s_win, t)); t += 10
    s_seq = 1
    seq.append(tcp_ack("c2s", c_port, s_port, c_seq, s_seq, c_win, "3-way handshake complete — persistent HTTP connection ESTABLISHED", t)); t += 4

    # 3. HLS Manifest GET & 200 OK
    m_req_len = 126 + len(host)
    seq.append(tcp_psh_ack("c2s", c_port, s_port, c_seq, s_seq, m_req_len, c_win, "HTTP GET /manifest.m3u8", t)); t += 1
    seq.append(http_get(host, "/manifest.m3u8", t)); t += 28
    c_seq += m_req_len

    manifest_body = (
        "#EXTM3U\n#EXT-X-VERSION:3\n"
        f"#EXT-X-STREAM-INF:BANDWIDTH={QUALITY_BANDWIDTH[quality]},"
        f"RESOLUTION={QUALITY_RESOLUTION[quality]}\n"
        f"[[{quality}/index.m3u8]]"
    )
    m_resp_len = 212
    seq.append(tcp_psh_ack("s2c", s_port, c_port, s_seq, c_seq, m_resp_len, s_win, "HTTP 200 OK (HLS manifest)", t)); t += 1
    seq.append(http_response(200, "OK", "application/vnd.apple.mpegurl", manifest_body, t, "212 B")); t += 5
    s_seq += m_resp_len
    seq.append(tcp_ack("c2s", c_port, s_port, c_seq, s_seq, c_win, "acknowledge HLS manifest", t)); t += 3

    # 4. Media Segments over TCP
    seg_bytes = QUALITY_SEGMENT_INT[quality]
    for i in range(1, 4):
        seg = f"segment{str(i).zfill(3)}.ts"
        seg_path = f"/{quality}/{seg}"
        s_req_len = 142 + len(host) + len(seg_path)
        seq.append(tcp_psh_ack("c2s", c_port, s_port, c_seq, s_seq, s_req_len, c_win, f"HTTP GET {seg_path}", t)); t += 1
        seq.append(http_get(host, seg_path, t, "Range: bytes=0-")); t += 24
        c_seq += s_req_len

        seq.append(tcp_psh_ack("s2c", s_port, c_port, s_seq, c_seq, seg_bytes, s_win, f"MPEG-TS chunk {seg} ({QUALITY_SEGMENT_MB[quality]} MB)", t)); t += 1
        body = f"[binary media segment, ~{QUALITY_SEGMENT_MB[quality]} MB — {QUALITY_BITRATE[quality]}]"
        seq.append(http_response(200, "OK", "video/MP2T", body, t, QUALITY_SEGMENT_BYTES[quality])); t += 4
        s_seq += seg_bytes
        seq.append(tcp_ack("c2s", c_port, s_port, c_seq, s_seq, c_win, f"acknowledge media segment {seg}", t)); t += 3

    # 5. TCP Connection Teardown (FIN-ACK)
    seq.append(tcp_fin_ack("c2s", c_port, s_port, c_seq, s_seq, c_win, "client closes stream connection (FIN, ACK)", t)); t += 9
    c_seq += 1
    seq.append(tcp_fin_ack("s2c", s_port, c_port, s_seq, c_seq, s_win, "server confirms stream teardown (FIN, ACK)", t)); t += 9
    s_seq += 1
    seq.append(tcp_ack("c2s", c_port, s_port, c_seq, s_seq, c_win, "final ACK — stream TCP connection CLOSED", t))

    return seq

