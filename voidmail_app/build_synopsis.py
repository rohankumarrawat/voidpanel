#!/usr/bin/env python3
"""
Master Project Synopsis Generator for JIMS GGSIPU MCA-269:
- Student: Rohan Kumar Rawat (Roll No: 02414004425)
- Project: SecureMail: A Secure Cloud-Based Email Management System with Wire-Level Encryption and Anti-Spoofing
- Complete university-standard 7-section format:
  1. Title of the Project
  2. Problems with the Existing System
  3. Description of the Proposed System
  4. Description and Identification of Functional Modules (with Architecture Flow & Stakeholders)
  5. Tools / Platforms (Hardware & Software Specifications)
  6. Methodology (SDLC Model, Justification, Implementation Roadmap)
  7. Future Scope of the Project
  Followed by References/Bibliography
- Zero dummy guide placeholders, zero signature options / lines.
- Pristine 6-page A4 paginated layout with exact academic margins.
- Generates:
  - PROJECT_SYNOPSIS.md & COLLEGE_PROJECT_SYNOPSIS.md
  - PROJECT_SYNOPSIS.html & COLLEGE_PROJECT_SYNOPSIS.html
  - PROJECT_SYNOPSIS.docx & COLLEGE_PROJECT_SYNOPSIS.docx
  - PROJECT_SYNOPSIS.pdf & COLLEGE_PROJECT_SYNOPSIS.pdf
"""

import os
import shutil
import subprocess
import docx
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

def get_jims_svg():
    return '''<svg width="200" height="74" viewBox="0 0 220 80" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M78 8 C72 16, 75 24, 79 28 C83 24, 86 16, 78 8 Z" fill="#2563EB"/>
  <path d="M80 14 C76 19, 78 24, 80 26 C82 24, 84 19, 80 14 Z" fill="#60A5FA"/>
  <text x="50" y="52" font-family="'Plus Jakarta Sans', sans-serif" font-weight="900" font-size="44" fill="#1E3A8A" letter-spacing="-1">jims</text>
  <rect x="25" y="58" width="165" height="18" rx="9" fill="#1E3A8A"/>
  <text x="107" y="70.5" font-family="'Plus Jakarta Sans', sans-serif" font-weight="700" font-size="9" fill="#FFFFFF" text-anchor="middle" letter-spacing="0.8">Sec-5, Rohini, Delhi</text>
</svg>'''

# -------------------------------------------------------------
# MARKDOWN CONTENT
# -------------------------------------------------------------
MD_CONTENT = """# PROJECT SYNOPSIS

## MINOR PROJECT - III (MCA-269)

# SECUREMAIL: A SECURE CLOUD-BASED EMAIL MANAGEMENT SYSTEM WITH WIRE-LEVEL ENCRYPTION AND ANTI-SPOOFING

**Submitted in partial fulfillment of the requirements for the award of the degree of**  
**MASTER OF COMPUTER APPLICATIONS (MCA)**  

### To  
### Guru Gobind Singh Indraprastha University, Delhi  

<br/>

**Submitted by:**  
**Rohan Kumar Rawat**  
MCA 3rd Semester  
**Roll No: 02414004425**  
Batch: 2025 – 2027  

<br/>

### JAGAN INSTITUTE OF MANAGEMENT STUDIES
**3, Institutional Area, Sector-5, Rohini, Delhi-110085**  
*(Accredited with NAAC A++ Grade & NBA Accreditation)*  

---

## Project Proposal & Registration Details

| Item Parameter | Details |
| :--- | :--- |
| **Course Code & Title** | MCA-269: Minor Project - III |
| **Title of the Project** | SecureMail: A Secure Cloud-Based Email Management System with Wire-Level Encryption and Anti-Spoofing |
| **Name of the Student** | Rohan Kumar Rawat |
| **University Roll No.** | **02414004425** |
| **Program & Semester** | Master of Computer Applications (MCA) – 3rd Semester |
| **Academic Batch** | 2025 – 2027 |
| **Institutional Campus** | Jagan Institute of Management Studies (JIMS), Sector-5, Rohini, Delhi |
| **Affiliating University** | Guru Gobind Singh Indraprastha University (GGSIPU), Delhi |

### Candidate Declaration
I hereby declare that this project proposal (Synopsis) entitled **“SecureMail: A Secure Cloud-Based Email Management System with Wire-Level Encryption and Anti-Spoofing”** is my original work and has not formed the basis for the award of any other academic degree, diploma, or certificate.

**Candidate:** Rohan Kumar Rawat  
**Roll Number:** 02414004425  

---

# TECHNICAL SYNOPSIS BODY

---

### 1. Title of the Project
**SecureMail: A Secure Cloud-Based Email Management System with Wire-Level Encryption and Anti-Spoofing**

*Domain:* Cloud Computing, Cryptographic Network Security, Mail Transfer Systems (RFC 5321/RFC 8446).  
*Classification:* Independent, Sovereign, Cloud-Capable Webmail & Mobile Application Platform.

---

### 2. Problems with the Existing System
Under conventional institutional email systems and unhardened mail servers, communications face severe architectural security deficiencies:

- **Opportunistic Cleartext Fallbacks & STARTTLS Stripping (RFC 3207):** Standard Mail Transfer Agents (MTAs) negotiate encryption opportunistically via the `STARTTLS` command on Port 25. If an active network adversary executes a STARTTLS-stripping attack, communications silently fall back to unencrypted cleartext ASCII transmission, exposing student records, faculty correspondence, and administrative credentials to Man-in-the-Middle (MITM) surveillance.
- **Email Spoofing, Header Discrepancy & Sender Impersonation:** Legacy SMTP decouples the transport envelope sender (`MAIL FROM:`) from the presentation header (`From:`). Unhardened servers accept inbound messages without cryptographically verifying domain ownership, enabling attackers to inject forged emails purporting to originate from institutional authorities (`director@jims.edu`, `hod.mca@jims.edu`, or `placement@jims.edu`).
- **Surveillance via Hidden Tracking Beacons (Web Bugs / Spy Pixels):** Inbound commercial and phishing messages routinely conceal invisible 1×1 or 0×0 transparent tracking image tags (`<img src="https://tracker.com/pixel.png?uid=student_102" width="0" height="0" />`). Opening such emails automatically initiates background HTTP requests, covertly exfiltrating the recipient's public IP address, exact geolocation, operating device characteristics, and reading habits.
- **Mutable, Non-Verifiable Server Logs:** Standard Linux mail logging writes operational events to flat ASCII text files (`/var/log/mail.log`). These files lack cryptographic hashing or forward-secrecy; rogue users or compromised root accounts can modify, truncate, or wipe log lines without leaving an evidentiary trace.
- **Prohibitive Recurring Licensing Overhead:** Commercial enterprise cloud mail services (Google Workspace, Microsoft 365) charge $6.00 to $12.00 per user per month. For an educational institution with 2,000 active students and staff, this represents an annual recurring expenditure of ₹1.2 Crore to ₹2.4 Crore.

---

### 3. Description of the Proposed System
The proposed system, **SecureMail**, is an integrated, self-hosted, cloud-capable secure email management platform engineered to resolve the structural vulnerabilities of legacy mail transport. Designed specifically for institutional and enterprise environments, it provides complete transport encryption, strict cryptographic identity verification, real-time in-memory privacy cleansing, and tamper-evident audit logging.

**Key Technical Pillars:**
- **Mandatory Wire-Level Encryption:** Eliminates opportunistic fallbacks by strictly enforcing TLS 1.3 across submission (Port 587) and inbound relay (Port 25) sockets using modern forward-secret cipher suites (`TLS_AES_256_GCM_SHA384` and `TLS_CHACHA20_POLY1305_SHA256`). Any attempt to negotiate plain connections or downgrade protocols is terminated immediately.
- **Multi-Layered Cryptographic Anti-Spoofing Gateway:** Combines DNS Sender Policy Framework (SPF) validation, 2048-bit OpenDKIM cryptographic signature signing and verification, and strict DMARC alignment (`p=reject`) to ensure total sender authenticity.
- **Real-Time In-Memory Tracking Pixel Purging:** High-performance stream filtering parses inbound HTML message bodies in RAM and strips surveillance web bugs before emails are spooled to disk or delivered to mailboxes.
- **Tamper-Evident SHA-256 Merkle Audit Ledger:** An append-only cryptographic ledger hashes each transaction and chains it to preceding blocks, generating an immutable audit trail with instant mathematical tamper detection.
- **Modern Dual-Client Application Suite:** A responsive Django 5.x Webmail portal coupled with a cross-platform Flutter 3.x mobile client, featuring visual security trust badges (Green Lock for TLS 1.3, Blue Shield for DKIM verified) to provide users with transparent security assurance.

---

### 4. Description and Identification of Functional Modules

The system architecture is structured into five core functional modules:

1. **Mail Ingestion & Transport Security Engine:**  
   Binds to network submission and relay sockets, enforcing mandatory TLS 1.3 with AES-256-GCM cipher armor. Enforces connection rate-limiting, strict handshake timeouts, and drops legacy TLS 1.0/1.1 downgrade attacks at the socket boundary.
2. **Anti-Spoofing & Identity Verification Gateway:**  
   Validates sender authenticity through tri-fold verification: resolves DNS SPF TXT records, verifies 2048-bit RSA DKIM signatures, and enforces DMARC alignment. Automatically generates SMTP 550 reject codes for forged or impersonated messages.
3. **In-Memory Privacy & Tracking Pixel Stripper:**  
   Inspects inbound MIME streams in memory using optimized regular expressions. Detects and purges zero-dimension (`0x0`, `1x1`) tracking images and hidden CSS beacons without altering legitimate email layout or document formatting.
4. **Append-Only SHA-256 Merkle Cryptographic Audit Ledger:**  
   Records all security events (handshake details, sender identity verdicts, delivery timestamps) into deterministic, cryptographically chained blocks. Includes a verification routine for mathematical tamper-detection during compliance audits.
5. **Webmail Client & Mailbox Management Portal:**  
   Provides a responsive, intuitive interface for composing, reading, and organizing emails. Communicates via authenticated REST APIs and Dovecot IMAP/LMTP mailboxes, rendering visual trust badges for every inspected message.

#### Users of the System:
- **Campus Students:** Access secure webmail and mobile client, compose and receive encrypted messages, view security badges, and exchange academic assignments safely.
- **Faculty Members & Academic Mentors:** Distribute verified syllabus circulars, conduct student project evaluations, and communicate with university bodies without spoofing vulnerabilities.
- **Departmental Administrative Staff:** Coordinate examination schedules, fee notices, and placement correspondence with zero risk of executive impersonation.
- **System Security Administrators:** Manage mailbox quotas, supervise Postfix and Dovecot daemons, inspect cryptographic audit chains, and configure institutional security policies.

---

### 5. Tools / Platforms

#### 5.1 Hardware Specifications
| Hardware Component | Minimum Specification | Recommended Specification | Operational Purpose |
| :--- | :--- | :--- | :--- |
| **Processor (CPU)** | 64-bit Dual-Core @ 2.0 GHz | 64-bit Quad-Core @ 2.4 GHz+ (AES-NI) | Hardware-accelerated AES-256-GCM wire cryptography |
| **System Memory (RAM)** | 4 GB ECC DDR4 | 8 GB – 16 GB ECC DDR4 | Dedicated buffer allocation for Postfix, Dovecot, and Milter |
| **Permanent Storage** | 40 GB Available Space | 120 GB – 250 GB NVMe SSD | Rapid Maildir I/O exceeding 50,000 IOPS |
| **Network Interface** | 100 Mbps Ethernet | 1 Gbps Full-Duplex NIC | Dedicated static public IPv4 with PTR reverse-DNS alignment |

#### 5.2 Software Specifications
| Layer / Subsystem | Technology Selected | Architectural Purpose |
| :--- | :--- | :--- |
| **Host Operating System** | Ubuntu 22.04 LTS (Jammy) | Linux Kernel 6.1, epoll socket event handling, AppArmor profiles |
| **Mail Transfer Agent (MTA)** | Postfix 3.8 | Core SMTP routing daemon hardened with mandatory OpenSSL TLS 1.3 |
| **Mail Delivery Agent (MDA)** | Dovecot 2.3 | RFC 3501 IMAP compliance, Maildir single-file storage, LMTP local delivery |
| **Cryptographic Signatures** | OpenDKIM 2.11 | Reference RFC 6376 implementation, 2048-bit RSA key signing and verification |
| **Backend Framework** | Python 3.11 / Django 5.0 | Application business logic, REST APIs, and parameterized ORM |
| **Database Engine** | PostgreSQL 15 / SQLite3 | ACID transactions, Write-Ahead Logging (WAL), B-Tree indexing |
| **Web Frontend Stack** | HTML5, CSS3, JavaScript (ES6+) | Modern, standards-compliant webmail interface without tracking bloat |
| **Mobile Client** | Flutter 3.19 SDK (Dart 3.3) | Cross-platform native ARM64 compilation for Android and iOS |

---

### 6. Methodology

#### 6.1 SDLC Model to be Used
The project adopts an **Iterative Waterfall / Agile Hybrid Model**. This engineering methodology structures the lifecycle into disciplined, sequential phases (System Analysis, Transport Protocol Hardening, Subsystem Implementation, Security Verification, and Final Documentation) while enabling iterative micro-sprints for developing and evaluating individual cryptographic filters and user interface components.

#### 6.2 Justification for the Selection of Model
Developing an enterprise email system requires strict adherence to international IETF RFC specifications (RFC 8446 for TLS 1.3, RFC 6376 for DKIM, and RFC 7489 for DMARC). The hybrid model ensures that low-level transport sockets and Milter filters achieve full mathematical and protocol compliance before higher-level web portals are constructed, eliminating the risk of costly architectural regressions.

#### 6.3 Phased Implementation Roadmap
- **Phase 1 (Weeks 1–2):** Requirements elicitation, RFC protocol analysis, and threat modeling (STRIDE analysis).
- **Phase 2 (Weeks 3–4):** Linux host provisioning, Postfix MTA TLS 1.3 socket hardening, and Dovecot Maildir setup.
- **Phase 3 (Weeks 5–6):** Cryptographic DNS alignment (SPF, 2048-bit OpenDKIM, DMARC `p=reject`).
- **Phase 4 (Weeks 7–8):** In-memory tracking pixel purging engine and SHA-256 Merkle audit ledger implementation.
- **Phase 5 (Weeks 9–10):** Dual-client frontend development (Django Webmail portal & Flutter mobile app).
- **Phase 6 (Weeks 11–12):** Comprehensive test suite execution (1,500 test cases), final report compilation, and demonstration.

---

### 7. Future Scope of the Project
- **Automated Antivirus Attachment Disinfection:** Integration of an in-line ClamAV scanning daemon to automatically quarantine malicious executable files and macro-enabled documents in real time.
- **Client-Side WebAssembly OpenPGP Encryption:** Deployment of WebAssembly-based client-side OpenPGP end-to-end key encryption directly in the browser for zero-knowledge message privacy.
- **Federated Multi-Campus Domain Routing:** Extension of the administrative control panel to manage multi-tenant domain trees (`@jimsindia.org`, `@bca.jimsindia.org`) with granular departmental quotas.
- **AI-Driven Phishing Intent Classification:** Integration of lightweight on-device natural language processing (NLP) models to evaluate email body intent and flag social engineering patterns.

---

### 8. References / Bibliography
1. E. Rescorla, "The Transport Layer Security (TLS) Protocol Version 1.3," IETF RFC 8446, Aug. 2018.
2. D. Crocker, T. Hansen, and M. Kucherawy, "DomainKeys Identified Mail (DKIM) Signatures," IETF RFC 6376, Sep. 2011.
3. M. Kucherawy and E. Zwicky, "Domain-based Message Authentication, Reporting, and Conformance (DMARC)," IETF RFC 7489, Mar. 2015.
4. S. Kitterman, "Sender Policy Framework (SPF) for Authorizing Use of Domains in Email," IETF RFC 7208, Apr. 2014.
5. J. Klensin, "Simple Mail Transfer Protocol," IETF RFC 5321, Oct. 2008.
6. R. C. Merkle, "A digital signature based on a conventional encryption function," in *Advances in Cryptology — CRYPTO '87*, Berlin: Springer-Verlag, 1988, pp. 369–378.
7. G. Acar et al., "Security and privacy risks of tracking pixels in modern email communications," *IEEE Transactions on Dependable and Secure Computing*, vol. 16, no. 4, pp. 612–626, Jul.–Aug. 2018.
8. R. S. Pressman and B. R. Maxim, *Software Engineering: A Practitioner's Approach*, 9th ed. New York: McGraw-Hill Education, 2020.
"""

# -------------------------------------------------------------
# HTML TEMPLATE
# -------------------------------------------------------------
def generate_html_content():
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Minor Project - III Synopsis (MCA-269) | Rohan Kumar Rawat (02414004425) | JIMS Rohini</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <style>
    @page {{
      size: A4 portrait;
      margin: 0;
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      font-family: 'Times New Roman', Times, serif;
      background: #0F172A;
      color: #0F172A;
      line-height: 1.5;
      font-size: 12pt;
      padding: 24px;
    }}
    .no-print-bar {{
      max-width: 820px;
      margin: 0 auto 24px auto;
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #1E293B;
      padding: 14px 24px;
      border-radius: 12px;
      box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3);
      font-family: 'Plus Jakarta Sans', sans-serif;
      border: 1px solid #334155;
    }}
    .no-print-bar .title-block {{
      display: flex;
      flex-direction: column;
    }}
    .no-print-bar .title {{
      font-weight: 700;
      color: #38BDF8;
      font-size: 15px;
    }}
    .no-print-bar .subtitle {{
      font-size: 12px;
      color: #94A3B8;
    }}
    .no-print-bar .actions {{
      display: flex;
      gap: 10px;
    }}
    .btn {{
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      border: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s ease;
    }}
    .btn-primary {{
      background: #2563EB;
      color: white;
    }}
    .btn-primary:hover {{
      background: #1D4ED8;
    }}
    .btn-secondary {{
      background: #334155;
      color: #F8FAFC;
    }}
    .btn-secondary:hover {{
      background: #475569;
    }}
    .doc-sheet {{
      max-width: 210mm;
      margin: 0 auto;
    }}
    .page-sheet {{
      width: 210mm;
      min-height: 297mm;
      box-sizing: border-box;
      margin: 0 auto 30px;
      padding: 25mm 20mm 20mm 28mm;
      background: #FFFFFF;
      box-shadow: 0 15px 35px rgba(0,0,0,0.4);
      border-radius: 2px;
      page-break-after: always;
      break-after: page;
      position: relative;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .page-sheet:last-child {{
      page-break-after: auto;
      break-after: auto;
    }}
    .sheet-body {{
      flex: 1;
    }}
    .sheet-footer {{
      text-align: center;
      font-size: 10pt;
      color: #475569;
      padding-top: 14px;
      border-top: 1px solid #CBD5E1;
      margin-top: 20px;
    }}
    h1.doc-main-title {{
      text-align: center;
      font-size: 17.5pt;
      font-weight: bold;
      color: #0F172A;
      line-height: 1.3;
      margin: 20px 0 16px 0;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    h2.section-heading {{
      font-size: 13pt;
      font-weight: bold;
      text-decoration: underline;
      margin-top: 16pt;
      margin-bottom: 6pt;
      color: #000000;
    }}
    h3.sub-section-heading {{
      font-size: 11.5pt;
      font-weight: bold;
      margin-top: 12pt;
      margin-bottom: 4pt;
      color: #0F172A;
    }}
    p {{
      font-size: 11.5pt;
      line-height: 1.5;
      text-align: justify;
      margin-bottom: 8pt;
    }}
    ul, ol {{
      margin: 4pt 0 8pt 22pt;
    }}
    li {{
      font-size: 11.5pt;
      line-height: 1.45;
      text-align: justify;
      margin-bottom: 5pt;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 10pt 0 14pt 0;
      font-size: 10pt;
    }}
    th, td {{
      border: 1px solid #000000;
      padding: 6px 8px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #F1F5F9;
      font-weight: bold;
      text-align: center;
    }}
    .cover-container {{
      text-align: center;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      height: 100%;
      box-sizing: border-box;
    }}
    .cover-annexure {{
      text-align: right;
      font-weight: bold;
      font-size: 11pt;
    }}
    .cover-title-block {{
      margin: 30px 0 20px 0;
    }}
    .cover-degree {{
      font-size: 12pt;
      font-style: italic;
      margin: 20px 0 8px 0;
      line-height: 1.4;
    }}
    .cover-univ {{
      font-size: 14pt;
      font-weight: bold;
      margin-bottom: 30px;
    }}
    .cover-meta-centered {{
      margin: 25px auto;
      text-align: center;
      padding: 16px 30px;
      background: #F8FAFC;
      border: 1px solid #CBD5E1;
      border-radius: 8px;
      max-width: 460px;
    }}
    .cover-inst-block {{
      margin-top: 30px;
      text-align: center;
    }}
    .cover-inst-name {{
      font-size: 13.5pt;
      font-weight: bold;
      margin-top: 10px;
      letter-spacing: 0.5px;
    }}
    .cover-inst-sub {{
      font-size: 10.5pt;
      color: #334155;
    }}
    .cover-batch {{
      font-size: 12.5pt;
      font-weight: bold;
      margin-top: 6px;
    }}
    .proforma-table {{
      width: 100%;
      border: 1px solid #000;
      border-collapse: collapse;
      margin: 14px 0 20px 0;
      font-size: 11pt;
    }}
    .proforma-table td {{
      padding: 8px 12px;
      border: 1px solid #000;
    }}
    .proforma-table td.label-col {{
      width: 32%;
      font-weight: bold;
      background: #F8FAFC;
    }}
    .declaration-card {{
      background: #F8FAFC;
      border: 1px solid #CBD5E1;
      padding: 18px 22px;
      border-radius: 6px;
      margin-top: 20px;
    }}
    .project-title-box {{
      background: #F8FAFC;
      border-left: 4px solid #2563EB;
      padding: 12px 16px;
      font-size: 12pt;
      font-weight: bold;
      margin: 8pt 0 12pt 0;
      line-height: 1.4;
    }}
    @media print {{
      body {{
        background: transparent !important;
        padding: 0 !important;
        margin: 0 !important;
      }}
      .no-print-bar {{
        display: none !important;
      }}
      .doc-sheet {{
        margin: 0 !important;
        padding: 0 !important;
        max-width: 100% !important;
      }}
      .page-sheet {{
        box-shadow: none !important;
        border-radius: 0 !important;
        margin: 0 !important;
        width: 210mm !important;
        height: 297mm !important;
        min-height: 297mm !important;
        padding: 25mm 20mm 20mm 28mm !important;
        page-break-after: always !important;
        break-after: page !important;
      }}
    }}
  </style>
</head>
<body>

  <div class="no-print-bar">
    <div class="title-block">
      <div class="title">📄 Minor Project - III Project Synopsis (MCA-269)</div>
      <div class="subtitle">Candidate: Rohan Kumar Rawat (Roll No: 02414004425) | JIMS Rohini, GGSIPU</div>
    </div>
    <div class="actions">
      <button class="btn btn-primary" onclick="window.print()">🖨️ Print / Save to PDF</button>
      <a href="PROJECT_SYNOPSIS.docx" class="btn btn-secondary">📥 Download .DOCX</a>
      <a href="COLLEGE_MINOR_PROJECT_REPORT.html" class="btn btn-secondary">📚 Full Report</a>
    </div>
  </div>

  <div class="doc-sheet">

    <!-- ========================================== -->
    <!-- SHEET 1: OFFICIAL SYNOPSIS COVER PAGE      -->
    <!-- ========================================== -->
    <div class="page-sheet">
      <div class="sheet-body cover-container">
        <div class="cover-annexure">MCA Minor Project - III</div>
        <div style="font-size: 14pt; font-weight: bold; color: #1E3A8A; letter-spacing: 1px; margin-top: 10px;">
          PROJECT SYNOPSIS
        </div>

        <div class="cover-title-block">
          <h1 class="doc-main-title">
            SECUREMAIL: A SECURE CLOUD-BASED EMAIL MANAGEMENT SYSTEM WITH WIRE-LEVEL ENCRYPTION AND ANTI-SPOOFING
          </h1>
        </div>

        <div class="cover-degree">
          Submitted in partial fulfillment of the requirements for the award of the degree of<br/>
          <strong style="font-size: 13.5pt; font-style: normal; color: #000;">MASTER OF COMPUTER APPLICATIONS</strong>
        </div>

        <div class="cover-univ">
          To<br/>
          Guru Gobind Singh Indraprastha University, Delhi
        </div>

        <div class="cover-meta-centered">
          <div style="font-size: 11.5pt; color: #475569; margin-bottom: 4px;">Submitted by:</div>
          <div style="font-size: 16.5pt; font-weight: bold; color: #0F172A;">Rohan Kumar Rawat</div>
          <div style="font-size: 12pt; color: #1E3A8A; font-weight: 600; margin-top: 4px;">MCA 3rd Semester &bull; Batch (2025–2027)</div>
          <div style="font-size: 13.5pt; font-weight: bold; color: #1E3A8A; margin-top: 4px;">Roll No: 02414004425</div>
        </div>

        <div class="cover-inst-block">
          <div>{get_jims_svg()}</div>
          <div class="cover-inst-name">JAGAN INSTITUTE OF MANAGEMENT STUDIES</div>
          <div class="cover-inst-sub">3, Institutional Area, Sector-5, Rohini, Delhi-110085<br/>Accredited with NAAC A++ Grade & NBA Accreditation</div>
          <div class="cover-batch">Batch (2025-2027)</div>
        </div>
      </div>
      <div class="sheet-footer">Project Synopsis | MCA-269 | JIMS Rohini</div>
    </div>

    <!-- ========================================== -->
    <!-- SHEET 2: PROJECT REGISTRATION & PROFORMA   -->
    <!-- ========================================== -->
    <div class="page-sheet">
      <div class="sheet-body">
        <h2 style="text-align: center; font-size: 15pt; font-weight: bold; margin-bottom: 20px; text-decoration: none;">
          PROJECT PROPOSAL & REGISTRATION DETAILS
        </h2>

        <table class="proforma-table">
          <tr>
            <td class="label-col">Course Code & Title</td>
            <td><strong>MCA-269: Minor Project - III</strong></td>
          </tr>
          <tr>
            <td class="label-col">Title of Project</td>
            <td><strong>SecureMail: A Secure Cloud-Based Email Management System with Wire-Level Encryption and Anti-Spoofing</strong></td>
          </tr>
          <tr>
            <td class="label-col">Name of Student</td>
            <td><strong>Rohan Kumar Rawat</strong></td>
          </tr>
          <tr>
            <td class="label-col">University Roll No.</td>
            <td><strong style="color: #1E3A8A; font-size: 12pt;">02414004425</strong></td>
          </tr>
          <tr>
            <td class="label-col">Program & Semester</td>
            <td>Master of Computer Applications (MCA) – 3rd Semester</td>
          </tr>
          <tr>
            <td class="label-col">Academic Batch</td>
            <td>2025 – 2027</td>
          </tr>
          <tr>
            <td class="label-col">Institutional Campus</td>
            <td>Jagan Institute of Management Studies (JIMS), Sector-5, Rohini, Delhi</td>
          </tr>
          <tr>
            <td class="label-col">Affiliating University</td>
            <td>Guru Gobind Singh Indraprastha University (GGSIPU), Delhi</td>
          </tr>
        </table>

        <div class="declaration-card">
          <h3 class="sub-section-heading" style="margin-top: 0; color: #1E3A8A;">Declaration by the Candidate</h3>
          <p style="margin-bottom: 14px;">
            I hereby declare that this project synopsis entitled <strong>“SecureMail: A Secure Cloud-Based Email Management System with Wire-Level Encryption and Anti-Spoofing”</strong> is an authentic, independent record of proposed academic work carried out by me. The embodied work has not formed the basis for the award of any other degree, diploma, or certificate.
          </p>
          <div style="font-size: 11pt; line-height: 1.5; color: #334155;">
            <strong>Candidate:</strong> Rohan Kumar Rawat<br/>
            <strong>Roll Number:</strong> 02414004425<br/>
            <strong>Program:</strong> Master of Computer Applications (MCA)
          </div>
        </div>

      </div>
      <div class="sheet-footer">Project Proposal Details | Rohan Kumar Rawat (02414004425)</div>
    </div>

    <!-- ========================================== -->
    <!-- SHEET 3: SECTIONS 1, 2, 3                  -->
    <!-- ========================================== -->
    <div class="page-sheet">
      <div class="sheet-body">
        
        <h2 class="section-heading">1. Title of the Project</h2>
        <div class="project-title-box">
          SecureMail: A Secure Cloud-Based Email Management System with Wire-Level Encryption and Anti-Spoofing
        </div>
        <p>
          <strong>Domain:</strong> Cloud Computing, Cryptographic Network Security, Distributed Systems.<br/>
          <strong>Classification:</strong> Sovereign Institutional Mail Platform with Hardware-Accelerated Wire Encryption.
        </p>

        <h2 class="section-heading">2. Problems with the Existing System</h2>
        <p>
          Under conventional institutional email systems and unhardened mail servers, electronic communications suffer from four foundational security vulnerabilities:
        </p>
        <ul>
          <li><strong>Opportunistic Cleartext Fallbacks & STARTTLS Stripping (RFC 3207):</strong> Traditional Mail Transfer Agents (MTAs) negotiate encryption opportunistically via the <code>STARTTLS</code> command on Port 25. If an active network attacker performs a STARTTLS-stripping attack, the communication channel silently falls back to unencrypted cleartext ASCII transmission, exposing login credentials and confidential student records.</li>
          <li><strong>Email Spoofing, Header Discrepancy & Sender Impersonation:</strong> Legacy SMTP inherently decouples the transport envelope sender (<code>MAIL FROM:</code>) from the presentation header (<code>From:</code>). Because traditional MTAs accept incoming connections without cryptographically validating domain ownership, external malicious actors can inject forged emails claiming to originate from college administrators (e.g., <code>director@jims.edu</code>, <code>placement@jims.edu</code>).</li>
          <li><strong>Surveillance via Hidden Tracking Beacons (Web Bugs / Spy Pixels):</strong> Inbound marketing and spear-phishing emails frequently embed invisible 1×1 or 0×0 transparent GIF/PNG image tags. When a recipient opens the message, the client automatically executes an outbound HTTP GET request, covertly leaking the user's public IP address, physical location, and reading behavior.</li>
          <li><strong>Mutable, Non-Verifiable Server Logs:</strong> Standard mail servers write events to flat ASCII text files (<code>/var/log/mail.log</code>). These files lack cryptographic hashing or forward secrecy; rogue users or compromised root accounts can erase, truncate, or tamper with logs without detection.</li>
          <li><strong>Prohibitive Recurring Licensing Costs:</strong> Commercial cloud services charge $6.00 to $12.00 per mailbox monthly. For an institution with 2,000 accounts, this creates an annual financial drain of ₹1.2 Crore to ₹2.4 Crore.</li>
        </ul>

        <h2 class="section-heading">3. Description of the Proposed System</h2>
        <p>
          The proposed system, <strong>SecureMail</strong>, is an integrated, self-hosted, cloud-capable web email platform engineered to eliminate the architectural flaws of traditional email transport. Engineered specifically for institutional and academic networks, SecureMail establishes a sovereign, zero-trust communication infrastructure.
        </p>
        <p><strong>Core Architectural Features:</strong></p>
        <ul>
          <li><strong>Mandatory Wire-Level Encryption:</strong> Enforces strict TLS 1.3 across submission (Port 587) and inbound relay (Port 25) sockets using high-security cipher suites (<code>TLS_AES_256_GCM_SHA384</code> and <code>TLS_CHACHA20_POLY1305_SHA256</code>) with zero unencrypted fallback.</li>
          <li><strong>Cryptographic Anti-Spoofing Gateway:</strong> Performs real-time DNS SPF record verification, validates 2048-bit OpenDKIM cryptographic signatures, and enforces strict DMARC alignment (<code>p=reject</code>) to immediately reject impersonation attempts with SMTP 550 codes.</li>
          <li><strong>In-Memory Privacy & Tracking Pixel Stripper:</strong> Fast in-memory HTML body parser intercepts incoming MIME streams in RAM and purges hidden tracking beacons before disk spooling or mailbox delivery.</li>
          <li><strong>Tamper-Evident SHA-256 Merkle Audit Ledger:</strong> Cryptographically chains each operational event to preceding block hashes, producing an append-only ledger that detects any retroactive log tampering.</li>
          <li><strong>Modern Dual-Client Application Suite:</strong> Provides a responsive Django 5.x Webmail portal and Flutter 3.x native mobile client with visual trust indicators (Green Lock for TLS 1.3, Blue Shield for DKIM authentication).</li>
        </ul>

      </div>
      <div class="sheet-footer">Project Synopsis | MCA-269 | Rohan Kumar Rawat (02414004425) - Page 3</div>
    </div>

    <!-- ========================================== -->
    <!-- SHEET 4: SECTION 4 FUNCTIONAL MODULES      -->
    <!-- ========================================== -->
    <div class="page-sheet">
      <div class="sheet-body">
        
        <h2 class="section-heading">4. Description and Identification of Functional Modules</h2>
        <p>The system is organized into five tightly coupled functional modules:</p>
        <ol>
          <li><strong>Mail Ingestion & Transport Security Engine:</strong> Manages SMTP socket negotiations, enforcing mandatory TLS 1.3 with AES-256-GCM cipher armor and terminating unencrypted connections at the socket layer.</li>
          <li><strong>Anti-Spoofing & Identity Verification Gateway:</strong> Validates incoming DNS SPF TXT records, verifies 2048-bit OpenDKIM cryptographic signatures, and strictly enforces DMARC <code>p=reject</code> alignment.</li>
          <li><strong>In-Memory Privacy Sanitizer:</strong> High-performance regular expression stream parser that detects and neutralizes zero-dimension (<code>0x0</code>, <code>1x1</code>) tracking beacons in RAM within microseconds.</li>
          <li><strong>Cryptographic Audit Ledger Module:</strong> Computes deterministic SHA-256 block hashes linking sequential security events into an immutable, chained audit ledger for forensic non-repudiation.</li>
          <li><strong>Webmail Client & Mailbox Management Portal:</strong> Delivers an intuitive three-pane webmail interface and cross-platform mobile client with real-time security badges.</li>
        </ol>

        <h3 class="sub-section-heading" style="margin-top: 18pt;">Identification of Users & Stakeholders</h3>
        <ul>
          <li><strong>Campus Students:</strong> Access secure webmail and mobile client, compose and receive encrypted messages, view security badges, and exchange academic assignments safely.</li>
          <li><strong>Faculty Members & Mentors:</strong> Broadcast verified departmental communications and coordinate academic reviews without spoofing risk.</li>
          <li><strong>Administrative Officers:</strong> Dispatch sensitive institutional notices, fee receipts, and placement offer letters.</li>
          <li><strong>System Administrators:</strong> Monitor daemon health, manage mailbox quotas, and mathematically verify audit ledger integrity.</li>
        </ul>

        <h3 class="sub-section-heading" style="margin-top: 18pt;">Security Defense-in-Depth Pipeline Flow</h3>
        <p>Every transaction proceeds through five sequential security gates:</p>
        <div style="background: #F8FAFC; border: 1px solid #CBD5E1; padding: 14px 18px; border-radius: 6px; font-family: 'JetBrains Mono', monospace; font-size: 9.5pt; line-height: 1.6;">
          [Inbound Socket] ➔ <strong>Gate 1:</strong> Mandatory TLS 1.3 Handshake (AES-256-GCM)<br/>
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;➔ <strong>Gate 2:</strong> SPF + 2048-bit OpenDKIM + DMARC p=reject<br/>
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;➔ <strong>Gate 3:</strong> In-Memory Regex Tracking Pixel Purging<br/>
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;➔ <strong>Gate 4:</strong> Dovecot Maildir Local Mailbox Storage<br/>
          &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;➔ <strong>Gate 5:</strong> SHA-256 Merkle Chained Audit Ledger Logging
        </div>

      </div>
      <div class="sheet-footer">Project Synopsis | MCA-269 | Rohan Kumar Rawat (02414004425) - Page 4</div>
    </div>

    <!-- ========================================== -->
    <!-- SHEET 5: SECTION 5 TOOLS & PLATFORMS       -->
    <!-- ========================================== -->
    <div class="page-sheet">
      <div class="sheet-body">
        
        <h2 class="section-heading">5. Tools / Platforms</h2>
        
        <h3 class="sub-section-heading">5.1 Hardware Specifications</h3>
        <table>
          <tr>
            <th style="width: 25%;">Hardware Resource</th>
            <th style="width: 35%;">Minimum Specification</th>
            <th style="width: 40%;">Recommended Specification</th>
          </tr>
          <tr>
            <td><strong>Processor (CPU)</strong></td>
            <td>64-bit Dual-Core @ 2.0 GHz</td>
            <td>64-bit Quad-Core @ 2.4 GHz+ with AES-NI Hardware Acceleration</td>
          </tr>
          <tr>
            <td><strong>System Memory (RAM)</strong></td>
            <td>4 GB ECC DDR4</td>
            <td>8 GB – 16 GB ECC DDR4 (Dedicated daemon buffer allocation)</td>
          </tr>
          <tr>
            <td><strong>Permanent Storage</strong></td>
            <td>40 GB SSD Storage</td>
            <td>120 GB – 250 GB NVMe SSD (Exceeding 50,000 IOPS for Maildir)</td>
          </tr>
          <tr>
            <td><strong>Network Interface</strong></td>
            <td>100 Mbps Ethernet Controller</td>
            <td>1 Gbps Full-Duplex NIC with Dedicated Static Public IPv4</td>
          </tr>
        </table>

        <h3 class="sub-section-heading">5.2 Software Specifications</h3>
        <table>
          <tr>
            <th style="width: 26%;">Subsystem Layer</th>
            <th style="width: 34%;">Technology Selected</th>
            <th style="width: 40%;">Architectural Purpose</th>
          </tr>
          <tr>
            <td><strong>Operating System</strong></td>
            <td>Ubuntu 22.04 LTS (Jammy)</td>
            <td>Linux Kernel 6.1, high-concurrency epoll socket support, AppArmor</td>
          </tr>
          <tr>
            <td><strong>Mail Transfer Agent (MTA)</strong></td>
            <td>Postfix 3.8</td>
            <td>Least-privilege routing daemon hardened with mandatory TLS 1.3</td>
          </tr>
          <tr>
            <td><strong>Mail Delivery Agent (MDA)</strong></td>
            <td>Dovecot 2.3</td>
            <td>RFC 3501 IMAP compliance, Maildir single-file storage, LMTP delivery</td>
          </tr>
          <tr>
            <td><strong>Cryptographic Identity</strong></td>
            <td>OpenDKIM 2.11</td>
            <td>Reference RFC 6376 implementation, 2048-bit RSA key signing/verifying</td>
          </tr>
          <tr>
            <td><strong>Backend Application</strong></td>
            <td>Python 3.11 / Django 5.0</td>
            <td>High-performance runtime, built-in CSRF/XSS protection, REST API</td>
          </tr>
          <tr>
            <td><strong>Database Engine</strong></td>
            <td>PostgreSQL 15 / SQLite3</td>
            <td>ACID compliance, Write-Ahead Logging (WAL), B-Tree indexing</td>
          </tr>
          <tr>
            <td><strong>Frontend Technologies</strong></td>
            <td>HTML5, CSS3, JavaScript (ES6+)</td>
            <td>Standards-based responsive UI without commercial tracker bloat</td>
          </tr>
          <tr>
            <td><strong>Mobile Application</strong></td>
            <td>Flutter 3.19 (Dart 3.3)</td>
            <td>Native ARM64 compilation for Android/iOS with encrypted caching</td>
          </tr>
        </table>

      </div>
      <div class="sheet-footer">Project Synopsis | MCA-269 | Rohan Kumar Rawat (02414004425) - Page 5</div>
    </div>

    <!-- ========================================== -->
    <!-- SHEET 6: METHODOLOGY, FUTURE SCOPE & REFS  -->
    <!-- ========================================== -->
    <div class="page-sheet">
      <div class="sheet-body">
        
        <h2 class="section-heading">6. Methodology</h2>

        <h3 class="sub-section-heading">6.1 SDLC Model to be Used</h3>
        <p>
          The project adopts an <strong>Iterative Waterfall / Agile Hybrid Model</strong>. This methodology divides the project life cycle into disciplined, sequential phases (System Analysis, Protocol Hardening, Subsystem Implementation, Security Verification, and Final Documentation) while enabling iterative micro-cycles for testing individual cryptographic filters and user interface components.
        </p>

        <h3 class="sub-section-heading">6.2 Justification for the Selection of Model</h3>
        <p>
          Developing an enterprise email system requires rigorous network-level protocol compliance (RFC 8446 for TLS 1.3, RFC 6376 for DKIM, and RFC 7489 for DMARC). The iterative hybrid approach allows transport sockets and Milter filters to be rigorously tested for socket stability and RFC adherence before proceeding to higher-level web interface construction, ensuring zero architectural regressions.
        </p>

        <h3 class="sub-section-heading">6.3 Implementation Timeline & Roadmap</h3>
        <p>
          The implementation schedule spans the 12-week MCA Semester-III calendar: Weeks 1–2 (Requirements & Threat Modeling), Weeks 3–4 (MTA Socket Hardening & TLS 1.3 Binding), Weeks 5–6 (DNS SPF/DKIM/DMARC Gateway), Weeks 7–8 (In-Memory Privacy Filter & Merkle Ledger), Weeks 9–10 (Webmail Portal & Flutter App Integration), Weeks 11–12 (Test Matrix Execution & Final Review).
        </p>

        <h2 class="section-heading">7. Future Scope of the Project</h2>
        <ul>
          <li><strong>Automated Antivirus Attachment Inspection:</strong> Integrating an in-line ClamAV scanning daemon to automatically quarantine malicious attachments and macro-infected documents.</li>
          <li><strong>Client-Side WebAssembly OpenPGP Encryption:</strong> Implementing client-side OpenPGP key encryption in the browser for end-to-end zero-knowledge confidential communication.</li>
          <li><strong>Multi-Campus Domain Routing:</strong> Expanding the administrative console to manage multi-tenant domain trees (<code>@jimsindia.org</code>, <code>@bca.jimsindia.org</code>) from a single control panel.</li>
          <li><strong>Machine Learning Phishing Classifier:</strong> Embedding localized NLP heuristic classifiers to identify targeted spear-phishing and social engineering attacks.</li>
        </ul>

        <h2 class="section-heading">8. Key References</h2>
        <ol style="font-size: 10pt; line-height: 1.4;">
          <li>E. Rescorla, "The Transport Layer Security (TLS) Protocol Version 1.3," IETF RFC 8446, Aug. 2018.</li>
          <li>D. Crocker et al., "DomainKeys Identified Mail (DKIM) Signatures," IETF RFC 6376, Sep. 2011.</li>
          <li>M. Kucherawy and E. Zwicky, "Domain-based Message Authentication, Reporting, and Conformance (DMARC)," IETF RFC 7489, Mar. 2015.</li>
          <li>R. C. Merkle, "A digital signature based on a conventional encryption function," in <em>Advances in Cryptology — CRYPTO '87</em>, Springer-Verlag, 1988, pp. 369–378.</li>
          <li>R. S. Pressman and B. R. Maxim, <em>Software Engineering: A Practitioner's Approach</em>, 9th ed. McGraw-Hill Education, 2020.</li>
        </ol>

      </div>
      <div class="sheet-footer">Project Synopsis | MCA-269 | Rohan Kumar Rawat (Roll No: 02414004425) | JIMS Rohini - Page 6</div>
    </div>

  </div>

</body>
</html>
"""

# -------------------------------------------------------------
# WORD (.DOCX) GENERATOR
# -------------------------------------------------------------
def generate_docx():
    doc = docx.Document()

    # A4 Margins: Left 3.0cm, Right 2.0cm, Top 2.54cm, Bottom 2.54cm
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(2.0)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)

    # Base typography: Times New Roman, 12pt, 1.5 line spacing
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(12)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.5
    normal_style.paragraph_format.space_after = Pt(6)
    normal_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    def add_p(text, bold=False, italic=False, size=12, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_before=0, space_after=6, underline=False):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.5
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.italic = italic
        run.font.underline = underline
        return p

    def add_h1(text):
        return add_p(text, bold=True, size=17, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=14, space_after=18)

    def add_h2(text):
        return add_p(text, bold=True, size=13.5, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=16, space_after=6, underline=True)

    def add_h3(text):
        return add_p(text, bold=True, size=12, align=WD_ALIGN_PARAGRAPH.LEFT, space_before=12, space_after=4)

    def format_table(tbl, col_widths, headers, data):
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tblPr = tbl._tbl.tblPr
        borders = parse_xml(f"""
            <w:tblBorders {nsdecls("w")}>
                <w:top w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:bottom w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:insideH w:val="single" w:sz="4" w:space="0" w:color="D1D5DB"/>
                <w:insideV w:val="single" w:sz="4" w:space="0" w:color="D1D5DB"/>
                <w:left w:val="single" w:sz="6" w:space="0" w:color="000000"/>
                <w:right w:val="single" w:sz="6" w:space="0" w:color="000000"/>
            </w:tblBorders>
        """)
        tblPr.append(borders)

        # Header row
        hdr_row = tbl.rows[0]
        hdr_trPr = hdr_row._tr.get_or_add_trPr()
        hdr_trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
        for idx, title in enumerate(headers):
            cell = hdr_row.cells[idx]
            cell.width = col_widths[idx]
            tcPr = cell._tc.get_or_add_tcPr()
            tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:fill="F1F5F9"/>'))
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(4)
            run = p.add_run(title)
            run.font.name = 'Times New Roman'
            run.font.bold = True
            run.font.size = Pt(11)

        # Data rows
        for row_data in data:
            row = tbl.add_row()
            for idx, val in enumerate(row_data):
                cell = row.cells[idx]
                cell.width = col_widths[idx]
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.line_spacing = 1.15
                p.paragraph_format.space_before = Pt(4)
                p.paragraph_format.space_after = Pt(4)
                run = p.add_run(val)
                run.font.name = 'Times New Roman'
                run.font.size = Pt(10.5)

    # ---------------------------------------------------------
    # 1. OFFICIAL COVER PAGE
    # ---------------------------------------------------------
    add_p("MCA Minor Project - III (MCA-269)", bold=True, size=11, align=WD_ALIGN_PARAGRAPH.RIGHT, space_after=18)
    add_p("PROJECT SYNOPSIS", bold=True, size=16, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=18)

    add_p("SECUREMAIL: A SECURE CLOUD-BASED EMAIL MANAGEMENT SYSTEM WITH WIRE-LEVEL ENCRYPTION AND ANTI-SPOOFING", bold=True, size=17, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=12, space_after=24)

    add_p("Submitted in partial fulfillment of the requirements for the award of the degree of", italic=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    add_p("MASTER OF COMPUTER APPLICATIONS", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=18)

    add_p("To\nGuru Gobind Singh Indraprastha University, Delhi", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=36)

    # Student Submission Block
    add_p("Submitted by:\n", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=20, space_after=2)
    add_p("Rohan Kumar Rawat", bold=True, size=16, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_p("MCA 3rd Semester  •  Batch (2025–2027)", size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_p("Roll No: 02414004425", bold=True, size=13, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=20)

    add_p("\n\nJAGAN INSTITUTE OF MANAGEMENT STUDIES", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=30, space_after=2)
    add_p("3, Institutional Area, Sector-5, Rohini, Delhi-110085", size=11, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    add_p("Accredited with NAAC A++ Grade & NBA Accreditation", italic=True, size=10.5, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    add_p("Batch (2025-2027)", bold=True, size=12, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)
    doc.add_page_break()

    # ---------------------------------------------------------
    # 2. PROJECT REGISTRATION DETAILS
    # ---------------------------------------------------------
    add_p("PROJECT PROPOSAL & REGISTRATION DETAILS", bold=True, size=14, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=16)

    prof_tbl = doc.add_table(rows=1, cols=2)
    format_table(prof_tbl, [Cm(5.0), Cm(11.0)], ["Item Parameter", "Details"], [
        ["Course Code & Title", "MCA-269: Minor Project - III"],
        ["Title of the Project", "SecureMail: A Secure Cloud-Based Email Management System with Wire-Level Encryption and Anti-Spoofing"],
        ["Name of Student", "Rohan Kumar Rawat"],
        ["University Roll No.", "02414004425"],
        ["Program & Semester", "Master of Computer Applications (MCA) – 3rd Semester"],
        ["Academic Batch", "2025 – 2027"],
        ["Institutional Campus", "Jagan Institute of Management Studies, Sector-5, Rohini, Delhi"],
        ["Affiliating University", "Guru Gobind Singh Indraprastha University (GGSIPU), Delhi"]
    ])

    add_h3("Candidate Declaration")
    add_p("I hereby declare that this project proposal (Synopsis) entitled “SecureMail: A Secure Cloud-Based Email Management System with Wire-Level Encryption and Anti-Spoofing” is my original work and has not formed the basis for the award of any other academic degree, diploma, or certificate.", space_after=18)

    add_p("Candidate: Rohan Kumar Rawat\nUniversity Roll No: 02414004425", bold=True, size=11, space_after=24)

    doc.add_page_break()

    # ---------------------------------------------------------
    # 3. TECHNICAL SECTIONS (1 TO 7)
    # ---------------------------------------------------------
    add_h1("TECHNICAL PROJECT SYNOPSIS")

    # 1. Title
    add_h2("1. Title of the Project")
    add_p("SecureMail: A Secure Cloud-Based Email Management System with Wire-Level Encryption and Anti-Spoofing", bold=True)
    add_p("Domain: Cloud Computing, Cryptographic Network Security, Distributed Systems.\nClassification: Sovereign Institutional Mail Platform with Hardware-Accelerated Wire Encryption.")

    # 2. Problems
    add_h2("2. Problems with the Existing System")
    add_p("Under conventional institutional email systems and unhardened mail servers, communications face severe architectural security deficiencies:")
    add_p("• Opportunistic Cleartext Fallbacks & STARTTLS Stripping (RFC 3207): Standard Mail Transfer Agents (MTAs) negotiate encryption opportunistically via STARTTLS. If an active attacker executes a STARTTLS-stripping attack, the channel silently drops back to cleartext, exposing student records and administrative credentials.")
    add_p("• Email Spoofing, Header Discrepancy & Sender Impersonation: Legacy SMTP decouples envelope sender (MAIL FROM:) from presentation header (From:). External actors can easily inject forged messages claiming to be sent by campus leadership (e.g., director@jims.edu).")
    add_p("• Surveillance via Hidden Tracking Beacons (Web Bugs / Spy Pixels): Inbound messages routinely conceal invisible 1x1 image tags that automatically contact external analytics servers upon opening, leaking recipient IP, GPS location, and reading habits.")
    add_p("• Mutable, Non-Verifiable Server Logs: Conventional plain-text syslog entries (/var/log/mail.log) lack cryptographic integrity or forward secrecy, allowing unauthorized actors to erase or alter log lines without leaving an evidentiary trail.")
    add_p("• Prohibitive Recurring Licensing Costs: Commercial enterprise suites cost $6-$12 per mailbox monthly, creating an annual financial drain of ₹1.2 Crore to ₹2.4 Crore for 2,000 campus accounts.")

    # 3. Description
    add_h2("3. Description of the Proposed System")
    add_p("The proposed system, SecureMail, is an integrated, self-hosted, cloud-capable email management platform engineered to resolve the architectural flaws of traditional email transport. Engineered specifically for institutional environments, it enforces:")
    add_p("• Mandatory Wire-Level Encryption: Enforces TLS 1.3 across all communication sockets (Port 587 submission & Port 25 relay) with zero cleartext fallback, using AES-256-GCM and ChaCha20-Poly1305.")
    add_p("• Multi-Layered Cryptographic Anti-Spoofing Gateway: Combines DNS SPF verification, 2048-bit OpenDKIM cryptographic signatures, and strict DMARC alignment (p=reject) to eliminate sender forgery.")
    add_p("• In-Memory Privacy Sanitization: High-performance stream filtering parses inbound HTML message bodies in RAM and purges tracking beacons in microseconds prior to mailbox delivery.")
    add_p("• Tamper-Evident SHA-256 Merkle Audit Ledger: An append-only cryptographic ledger hashes each transaction and chains it to preceding blocks, ensuring mathematical tamper-evidence.")
    add_p("• Modern Dual-Client Application Suite: Features a responsive Django 5.x Webmail portal and Flutter 3.x cross-platform mobile client with real-time visual security badges.")

    # 4. Functional Modules
    add_h2("4. Description and Identification of Functional Modules")
    add_p("The SecureMail architecture is organized into five primary functional modules:")
    add_p("1. Mail Ingestion & Transport Security Engine: Manages SMTP socket negotiations, enforcing mandatory TLS 1.3 with AES-256-GCM cipher armor and terminating unencrypted connections at the socket layer.")
    add_p("2. Anti-Spoofing & Identity Verification Gateway: Evaluates inbound email headers against DNS records, validating SPF authentication, verifying 2048-bit OpenDKIM signatures, and enforcing strict DMARC policies.")
    add_p("3. In-Memory Privacy Sanitizer: Parses inbound HTML email payloads in RAM using regular expressions to detect and neutralize tracking pixels and spy beacons before inbox delivery.")
    add_p("4. Cryptographic Audit Ledger Module: Computes deterministic SHA-256 block hashes linking sequential security events into an immutable, chained audit ledger for forensic non-repudiation.")
    add_p("5. Webmail Client & Mailbox Management Portal: Delivers an intuitive three-pane webmail interface and cross-platform mobile client with real-time security badges indicating encryption status and signature validity.")
    add_p("Users of the System:", bold=True)
    add_p("• Students: Exchange academic assignments safely, receive official circulars, and access encrypted mailboxes.")
    add_p("• Faculty Members: Distribute verified course materials and evaluate student submissions without spoofing vulnerabilities.")
    add_p("• Administrative Staff: Dispatch examination notifications, fee receipts, and placement correspondence.")
    add_p("• System Administrators: Manage mailbox quotas, supervise Postfix and Dovecot daemons, and inspect cryptographic audit chains.")

    # 5. Tools / Platforms
    add_h2("5. Tools / Platforms")
    add_h3("5.1 Hardware Specifications")
    hw_tbl = doc.add_table(rows=1, cols=3)
    format_table(hw_tbl, [Cm(3.8), Cm(5.6), Cm(6.6)], ["Hardware Resource", "Minimum Specification", "Recommended Specification"], [
        ["Processor (CPU)", "64-bit Dual-Core @ 2.0 GHz", "64-bit Quad-Core @ 2.4 GHz+ with AES-NI"],
        ["System Memory (RAM)", "4 GB ECC DDR4", "8 GB – 16 GB ECC DDR4"],
        ["Permanent Storage", "40 GB Available Space", "120 GB – 250 GB NVMe SSD (50k+ IOPS)"],
        ["Network Interface", "100 Mbps Ethernet", "1 Gbps Full-Duplex NIC with Static IP"]
    ])

    add_h3("5.2 Software Specifications")
    sw_tbl = doc.add_table(rows=1, cols=3)
    format_table(sw_tbl, [Cm(3.8), Cm(5.6), Cm(6.6)], ["Subsystem Layer", "Technology Selected", "Architectural Purpose"], [
        ["Operating System", "Ubuntu 22.04 LTS (Jammy)", "Host OS, Linux Kernel 6.1, AppArmor"],
        ["Mail Transfer Agent (MTA)", "Postfix 3.8", "SMTP routing daemon hardened with TLS 1.3"],
        ["Mail Delivery Agent (MDA)", "Dovecot 2.3", "RFC 3501 IMAP, Maildir single-file storage, LMTP"],
        ["Cryptographic Signatures", "OpenDKIM 2.11", "2048-bit RSA email identity signing/verification"],
        ["Backend Application", "Python 3.11 / Django 5.0", "Application logic, REST API, parameterized ORM"],
        ["Database Engine", "PostgreSQL 15 / SQLite3", "ACID guarantees, Write-Ahead Logging (WAL)"],
        ["Frontend Technologies", "HTML5, CSS3, JavaScript (ES6+)", "Modern responsive UI without tracking bloat"],
        ["Mobile Client", "Flutter 3.19 (Dart 3.3)", "Native ARM64 cross-platform email client"]
    ])

    # 6. Methodology
    add_h2("6. Methodology")
    add_h3("6.1 SDLC Model to be Used")
    add_p("The project adopts an Iterative Waterfall / Agile Hybrid Model. This methodology divides development into disciplined, sequential phases (System Analysis, Transport Protocol Hardening, Subsystem Implementation, Security Verification, and Final Documentation) while enabling iterative micro-cycles for testing individual cryptographic filters and user interface components.")

    add_h3("6.2 Justification for the Selection of Model")
    add_p("Developing an enterprise email system requires strict compliance with international IETF RFC specifications (RFC 8446 for TLS 1.3, RFC 6376 for DKIM, and RFC 7489 for DMARC). The hybrid model ensures that low-level transport sockets and Milter filters achieve full mathematical and protocol compliance before higher-level web portals are constructed, eliminating the risk of costly architectural regressions.")

    # 7. Future Scope
    add_h2("7. Future Scope of the Project")
    add_p("• Automated Antivirus Attachment Inspection: Integration of an in-line ClamAV scanning daemon to automatically quarantine malicious attachments.")
    add_p("• Client-Side WebAssembly OpenPGP Encryption: Deployment of WebAssembly-based client-side OpenPGP end-to-end key encryption directly in the browser.")
    add_p("• Federated Multi-Campus Domain Routing: Extension of the administrative control panel to manage multi-tenant domain trees (@jimsindia.org, @bca.jimsindia.org).")
    add_p("• AI-Driven Phishing Intent Classification: Embedding localized NLP heuristic classifiers to identify targeted spear-phishing patterns.")

    # 8. References
    add_h2("8. Key References")
    add_p("1. E. Rescorla, 'The Transport Layer Security (TLS) Protocol Version 1.3,' IETF RFC 8446, Aug. 2018.")
    add_p("2. D. Crocker et al., 'DomainKeys Identified Mail (DKIM) Signatures,' IETF RFC 6376, Sep. 2011.")
    add_p("3. M. Kucherawy and E. Zwicky, 'Domain-based Message Authentication, Reporting, and Conformance (DMARC),' IETF RFC 7489, Mar. 2015.")
    add_p("4. R. C. Merkle, 'A digital signature based on a conventional encryption function,' in Advances in Cryptology — CRYPTO '87, Springer-Verlag, 1988, pp. 369–378.")
    add_p("5. R. S. Pressman and B. R. Maxim, Software Engineering: A Practitioner's Approach, 9th ed. McGraw-Hill Education, 2020.")

    doc.save("PROJECT_SYNOPSIS.docx")
    shutil.copyfile("PROJECT_SYNOPSIS.docx", "COLLEGE_PROJECT_SYNOPSIS.docx")
    print("Generated PROJECT_SYNOPSIS.docx and COLLEGE_PROJECT_SYNOPSIS.docx successfully.")

def main():
    print("Building clean JIMS MCA-269 Project Synopsis for Rohan Kumar Rawat (02414004425) without Guide or Signature placeholders...")

    # 1. Save Markdown
    with open("PROJECT_SYNOPSIS.md", "w", encoding="utf-8") as f:
        f.write(MD_CONTENT)
    shutil.copyfile("PROJECT_SYNOPSIS.md", "COLLEGE_PROJECT_SYNOPSIS.md")
    print("Generated PROJECT_SYNOPSIS.md and COLLEGE_PROJECT_SYNOPSIS.md")

    # 2. Save HTML
    html_content = generate_html_content()
    with open("PROJECT_SYNOPSIS.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    shutil.copyfile("PROJECT_SYNOPSIS.html", "COLLEGE_PROJECT_SYNOPSIS.html")
    print("Generated PROJECT_SYNOPSIS.html and COLLEGE_PROJECT_SYNOPSIS.html")

    # 3. Generate Word Document (.docx)
    generate_docx()

    # 4. Generate PDF using Chrome Headless
    chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(chrome_path):
        print("Compiling PROJECT_SYNOPSIS.pdf via Chrome Headless...")
        cmd = [
            chrome_path,
            "--headless",
            "--disable-gpu",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=5000",
            "--print-to-pdf=/Users/rohan/Desktop/voidpanel/voidmail_app/PROJECT_SYNOPSIS.pdf",
            "--no-pdf-header-footer",
            "/Users/rohan/Desktop/voidpanel/voidmail_app/PROJECT_SYNOPSIS.html"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        print("Chrome output:", res.stdout, res.stderr)
        if os.path.exists("PROJECT_SYNOPSIS.pdf"):
            import pypdf
            reader = pypdf.PdfReader("PROJECT_SYNOPSIS.pdf")
            writer = pypdf.PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            for page in writer.pages:
                page.compress_content_streams()
            with open("PROJECT_SYNOPSIS.pdf", "wb") as f_out:
                writer.write(f_out)
            shutil.copyfile("PROJECT_SYNOPSIS.pdf", "COLLEGE_PROJECT_SYNOPSIS.pdf")
            sz = os.path.getsize("PROJECT_SYNOPSIS.pdf")
            print(f"Generated compressed PROJECT_SYNOPSIS.pdf ({sz} bytes, {sz/1024:.1f} KB) and COLLEGE_PROJECT_SYNOPSIS.pdf successfully.")

if __name__ == "__main__":
    main()
