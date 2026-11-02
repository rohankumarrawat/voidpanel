# PROJECT SYNOPSIS

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
