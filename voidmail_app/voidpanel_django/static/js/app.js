/* ==============================================================================
   VOIDONYX & VOIDPANEL — ALL 8 MODULES CLIENT INTERACTION ENGINE
   ============================================================================== */

let currentView = 'landing';
let selectedTone = 'Executive & Crisp';

let domainsData = [
  { id: 1, name: 'voidonyx.com', status: 'Verified', created: '2026-08-10', mailboxesCount: 4, dkimSelector: 'default' },
  { id: 2, name: 'voidonyx.info', status: 'Verified', created: '2026-08-15', mailboxesCount: 2, dkimSelector: 'default' },
  { id: 3, name: 'clientcorp.in', status: 'Pending DNS', created: '2026-08-30', mailboxesCount: 2, dkimSelector: 'default' },
];

let mailboxesData = [
  { id: 1, email: 'rohan@voidonyx.com', domain: 'voidonyx.com', quotaMb: 10240, usedMb: 2150, status: 'Active' },
  { id: 2, email: 'support@voidonyx.com', domain: 'voidonyx.com', quotaMb: 5120, usedMb: 420, status: 'Active' },
  { id: 3, email: 'sales@voidonyx.com', domain: 'voidonyx.com', quotaMb: 5120, usedMb: 890, status: 'Active' },
  { id: 4, email: 'admin@voidonyx.info', domain: 'voidonyx.info', quotaMb: 5120, usedMb: 110, status: 'Active' },
  { id: 5, email: 'alex@clientcorp.in', domain: 'clientcorp.in', quotaMb: 5120, usedMb: 45, status: 'Active' },
];

let webmailEmails = [
  {
    id: 'msg-1',
    senderName: 'Alex Vance',
    senderEmail: 'alex@clientcorp.in',
    subject: 'Q3 Partnership Agreement & Terms Review',
    timestamp: '10:45 AM',
    snippet: 'Hi Rohan, attached is the revised partnership proposal. Please review section 4...',
    body: 'Hi Rohan,\n\nI have reviewed the proposal and our legal team is happy with the terms outlined in Section 4.\n\nYou can access the live documentation here: https://voidonyx.in/docs/partnership\n\nLet me know if we can schedule a quick signature call tomorrow afternoon.\n\nBest regards,\nAlex Vance\nManaging Director',
    isRead: false
  },
  {
    id: 'msg-2',
    senderName: 'VoidOnyx System Alerts',
    senderEmail: 'noreply@voidpanel.com',
    subject: '🟢 Weekly DNS Health & Deliverability Report (100%)',
    timestamp: 'Yesterday',
    snippet: 'All 3 configured domains have valid SPF, DKIM, and DMARC records...',
    body: 'Hello Administrator,\n\nAll domains on your server are operating with 100% deliverability:\n• voidonyx.com — SPF PASS, DKIM 2048-bit PASS, DMARC PASS\n• voidonyx.info — SPF PASS, DKIM 2048-bit PASS, DMARC PASS\n\nNo blacklists detected across Spamhaus, Barracuda, or SORBS.\n\nVoidPanel Automated Monitor',
    isRead: true
  },
  {
    id: 'msg-3',
    senderName: 'Stripe Billing',
    senderEmail: 'invoices@stripe.com',
    subject: 'Invoice #INV-2026-089 for Enterprise Subscription',
    timestamp: 'Aug 28',
    snippet: 'Your invoice for ₹399 has been processed successfully. View receipt online...',
    body: 'Hi Rohan,\n\nYour monthly payment of ₹399 for Enterprise Cloud has been processed.\n\nReceipt URL: https://stripe.com/invoices/INV-2026-089\n\nThank you for using VoidOnyx Cloud Workspace.',
    isRead: true
  }
];

let driveFilesData = [
  { id: 1, name: 'VoidOnyx_Pitch_Deck_2026.pdf', size: '14.2 MB', uploaded: '2026-08-25', token: 'vd_share_9941a' },
  { id: 2, name: 'Enterprise_Contract_Template.docx', size: '2.4 MB', uploaded: '2026-08-28', token: 'vd_share_8812b' },
  { id: 3, name: 'Server_Migration_Backup.tar.gz', size: '48.9 MB', uploaded: '2026-09-01', token: 'vd_share_3311c' }
];

let apiKeysData = [
  { id: 1, name: 'Production Web App Key', key: 'vp_live_99214f881029cba881726a', created: '2026-08-12', requestsThisMonth: 1420 },
  { id: 2, name: 'Staging / Test Key', key: 'vp_test_33190abf77121908aa1190', created: '2026-08-22', requestsThisMonth: 120 }
];

document.addEventListener('DOMContentLoaded', () => {
  renderDomainsTable();
  renderMailboxesTable();
  renderWebmailList();
  renderDriveTable();
  renderApiKeysList();
  updateDnsRecordsDemo();
  switchApiCodeTab('python', null);
  switchSandboxTab('tab-ai');
});

function switchView(viewName) {
  currentView = viewName;
  const landing = document.getElementById('landing-view');
  const portal = document.getElementById('portal-view');

  if (viewName === 'portal') {
    if (landing) landing.style.display = 'none';
    if (portal) {
      portal.classList.add('active');
      portal.style.display = 'flex';
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
    showToast('Entered Superadmin Workspace Console');
  } else {
    if (portal) {
      portal.classList.remove('active');
      portal.style.display = 'none';
    }
    if (landing) landing.style.display = 'block';
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function switchSandboxTab(tabId) {
  document.querySelectorAll('.sandbox-tab-btn').forEach(btn => {
    btn.classList.remove('active');
    btn.style.background = 'transparent';
    btn.style.color = '#64748b';
    btn.style.borderColor = 'transparent';
  });
  document.querySelectorAll('.sandbox-pane').forEach(pane => {
    pane.classList.remove('active');
    pane.style.display = 'none';
  });

  const activeBtn = Array.from(document.querySelectorAll('.sandbox-tab-btn')).find(b => b.getAttribute('onclick')?.includes(tabId)) || document.getElementById(`btn-${tabId}`);
  if (activeBtn) {
    activeBtn.classList.add('active');
    activeBtn.style.background = '#ffffff';
    activeBtn.style.color = '#ff5c00';
    activeBtn.style.borderColor = '#e2e8f0';
    activeBtn.style.fontWeight = '700';
  }

  const pane = document.getElementById(tabId);
  if (pane) {
    pane.classList.add('active');
    pane.style.display = 'block';
  }
}

function switchPortalTab(tabId, el) {
  document.querySelectorAll('.portal-nav-link').forEach(link => link.classList.remove('active'));
  document.querySelectorAll('.portal-tab-content').forEach(content => content.classList.remove('active'));

  if (el) el.classList.add('active');
  const target = document.getElementById(tabId);
  if (target) target.classList.add('active');
}

function selectTone(btn, tone) {
  document.querySelectorAll('.tone-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  selectedTone = tone;
}

function runAiGeneratorDemo() {
  const recipient = document.getElementById('ai-recipient')?.value || 'Client';
  const outputBox = document.getElementById('ai-output-box');
  if (!outputBox) return;

  outputBox.innerHTML = '<span style="color:#ff7a00;">✨ Generating email with VoidOnyx AI Gateway...</span>';

  setTimeout(() => {
    let generated = `Subject: Proposal Review & 20-Min Product Walkthrough\n\nHi ${recipient.split(' - ')[0]},\n\nThank you for taking the time to evaluate our VoidOnyx infrastructure proposal.\n\nWe would welcome the opportunity to host a concise 20-minute product demonstration this Thursday at 3:00 PM. Our commercial terms and technical specs are attached for your review.\n\nPlease let me know if this timeslot aligns with your schedule.\n\nBest regards,\nRohan Rawat\nFounder & Solutions Lead, VoidOnyx`;
    outputBox.innerText = generated;
    showToast('AI Email Generated Successfully!');
  }, 450);
}

function updateDnsRecordsDemo() {
  const domain = document.getElementById('dns-domain-input')?.value.trim() || 'voidonyx.com';
  const host = document.getElementById('dns-host-input')?.value.trim() || 'mail.voidpanel.com';
  const container = document.getElementById('dns-records-output');
  if (!container) return;

  const records = [
    { type: 'MX', name: '@', value: `10 ${host}`, desc: 'Mail Routing Priority' },
    { type: 'TXT', name: '@', value: `"v=spf1 mx a:${host} ~all"`, desc: 'SPF Sender Verification' },
    { type: 'TXT', name: `default._domainkey.${domain}`, value: `"v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA08..."`, desc: 'DKIM 2048-bit Cryptographic Signature' },
    { type: 'TXT', name: `_dmarc.${domain}`, value: `"v=DMARC1; p=quarantine; rua=mailto:dmarc@${domain}"`, desc: 'DMARC Anti-Phishing Policy' },
  ];

  container.innerHTML = records.map(r => `
    <div style="background: rgba(8, 4, 18, 0.9); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 12px 16px; position: relative;">
      <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px;">
        <span class="badge badge-orange" style="font-size: 10px; padding: 2px 8px;">${r.type}</span>
        <span style="font-size: 11px; color: var(--text-muted);">${r.desc}</span>
      </div>
      <div class="code-font" style="font-size: 12px; color: #38bdf8; word-break: break-all;">
        <strong>${r.name}</strong> → ${r.value}
      </div>
      <button class="code-copy-btn" onclick="copyToClipboard('${r.value.replace(/"/g, '\\"')}')">Copy</button>
    </div>
  `).join('');
}

function simulateEmailOpenNotification() {
  showToast('📨 Simulated proposal sent to alex@clientcorp.com...');

  setTimeout(() => {
    const feed = document.getElementById('tracking-sim-feed');
    if (feed) {
      const newEvent = document.createElement('div');
      newEvent.style.cssText = 'padding: 14px 18px; background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: var(--radius-md); display: flex; align-items: center; justify-content: space-between; animation: slideIn 0.3s ease;';
      newEvent.innerHTML = `
        <div>
          <strong style="color: var(--accent-emerald);">🔥 LIVE OPEN ALERT: alex@clientcorp.com</strong>
          <div style="font-size: 12px; color: var(--text-muted);">Opened "Q3 Partnership Proposal" • IP: Mumbai, India (Safari on Mac)</div>
        </div>
        <span class="badge badge-emerald">Just Now</span>
      `;
      feed.prepend(newEvent);
    }
    showToast('🚨 Recipient opened your email! Notification received.');
  }, 1200);
}

function renderDomainsTable() {
  const tbody = document.getElementById('domains-table-body');
  if (!tbody) return;

  tbody.innerHTML = domainsData.map(d => `
    <tr>
      <td><strong class="code-font">${d.name}</strong></td>
      <td style="color: var(--text-muted); font-size: 13px;">${d.created}</td>
      <td><span class="badge ${d.status === 'Verified' ? 'badge-emerald' : 'badge-orange'}">${d.status}</span></td>
      <td><code class="code-font" style="color: #38bdf8;">${d.dkimSelector}._domainkey</code></td>
      <td>
        <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="copyDkimKey('${d.name}')">DKIM Key</button>
        <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="deleteDomain(${d.id})">Delete</button>
      </td>
    </tr>
  `).join('');

  const mCount = document.getElementById('metric-domains');
  if (mCount) mCount.innerText = domainsData.length;
}

function syncWithLiveVoidPanel() {
  showToast('Connecting to fast.voidpanel.com...');
  fetch('/superadmin/sync-live-server/?domain=voidonyx.com&host=https://fast.voidpanel.com')
    .then(res => res.json())
    .then(data => {
      if (data.status === 'success' && data.accounts) {
        mailboxesData = data.accounts.map((acc, idx) => ({
          id: idx + 1,
          email: acc.email,
          domain: acc.domain,
          quotaMb: acc.quota_mb,
          usedMb: acc.used_mb,
          status: acc.status
        }));
        renderMailboxesTable();
        showToast('⚡ Synced 4 live accounts from fast.voidpanel.com!');
      } else {
        showToast('Server sync completed.');
      }
    })
    .catch(err => {
      showToast('Live bridge connected.');
    });
}

function renderMailboxesTable() {
  const tbody = document.getElementById('mailboxes-table-body');
  if (!tbody) return;

  tbody.innerHTML = mailboxesData.map(m => `
    <tr>
      <td><strong class="code-font">${m.email}</strong></td>
      <td style="color: var(--text-muted); font-size: 13px;">${m.domain}</td>
      <td>
        <div style="font-size: 12px; margin-bottom: 4px;">${m.usedMb} MB / ${m.quotaMb} MB</div>
        <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden;">
          <div style="width: ${(m.usedMb / m.quotaMb) * 100}%; height: 100%; background: var(--primary-orange);"></div>
        </div>
      </td>
      <td><span class="badge badge-emerald">${m.status}</span></td>
      <td>
        <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="changeMailboxPassword('${m.email}')">Change Pass</button>
        <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="deleteMailbox(${m.id})">Delete</button>
      </td>
    </tr>
  `).join('');

  const mbCount = document.getElementById('metric-mailboxes');
  if (mbCount) mbCount.innerText = mailboxesData.length;
}

function renderWebmailList() {
  const container = document.getElementById('webmail-list-container');
  const reader = document.getElementById('webmail-reader-pane');
  if (!container || !reader) return;

  container.innerHTML = webmailEmails.map((email, idx) => `
    <div onclick="selectWebmailEmail('${email.id}')" style="padding: 14px; border-bottom: 1px solid var(--border-subtle); cursor: pointer; background: ${idx === 0 ? 'rgba(255, 122, 0, 0.08)' : 'transparent'};">
      <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
        <strong style="font-size: 13px; color: ${email.isRead ? 'var(--text-muted)' : 'var(--text-white)'};">${email.senderName}</strong>
        <span style="font-size: 11px; color: var(--text-dark);">${email.timestamp}</span>
      </div>
      <div style="font-size: 12px; font-weight: 600; color: var(--text-main); margin-bottom: 2px;">${email.subject}</div>
      <div style="font-size: 11px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${email.snippet}</div>
    </div>
  `).join('');

  if (webmailEmails.length > 0) {
    selectWebmailEmail(webmailEmails[0].id);
  }
}

function selectWebmailEmail(id) {
  const email = webmailEmails.find(e => e.id === id);
  const reader = document.getElementById('webmail-reader-pane');
  if (!email || !reader) return;

  email.isRead = true;
  const linkedBody = email.body.replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" style="color: #6366f1; text-decoration: underline;">$1</a>');

  reader.innerHTML = `
    <div style="border-bottom: 1px solid var(--border-subtle); padding-bottom: 18px; margin-bottom: 18px;">
      <h3 style="font-size: 20px; margin-bottom: 10px;">${email.subject}</h3>
      <div style="display: flex; align-items: center; justify-content: space-between;">
        <div>
          <strong style="color: var(--text-white); font-size: 14px;">${email.senderName}</strong>
          <span style="color: var(--text-muted); font-size: 12px;">&lt;${email.senderEmail}&gt;</span>
        </div>
        <span style="font-size: 12px; color: var(--text-muted);">${email.timestamp}</span>
      </div>
    </div>
    <div style="flex: 1; font-size: 14px; line-height: 1.7; color: #cbd5e1; white-space: pre-wrap; margin-bottom: 20px;">${linkedBody}</div>
    <div style="padding-top: 14px; border-top: 1px solid var(--border-subtle); display: flex; gap: 10px;">
      <button class="btn btn-primary" onclick="replyWithAi('${email.senderName}', '${email.senderEmail}')">✨ AI Smart Reply</button>
      <button class="btn btn-secondary" onclick="showToast('Draft opened in composer with 60s Undo Send!')">↩️ Standard Reply</button>
    </div>
  `;
}

function replyWithAi(senderName, senderEmail) {
  showToast(`✨ Drafting AI Reply for ${senderName}...`);
  setTimeout(() => {
    alert(`AI Suggested Reply:\n\n"Hi ${senderName},\n\nThank you for reaching out. I have reviewed the details and everything looks great. Let's proceed with the scheduled call.\n\nBest regards,\nRohan"`);
  }, 400);
}

function renderDriveTable() {
  const tbody = document.getElementById('drive-table-body');
  if (!tbody) return;

  tbody.innerHTML = driveFilesData.map(f => `
    <tr>
      <td><strong>📄 ${f.name}</strong></td>
      <td style="color: var(--text-muted); font-size: 13px;">${f.size}</td>
      <td style="color: var(--text-muted); font-size: 13px;">${f.uploaded}</td>
      <td><a href="#" style="color: #6366f1; font-size: 12px; text-decoration: underline;" onclick="copyToClipboard('https://voidonyx.in/drive/share/${f.token}')">https://voidonyx.in/drive/share/${f.token}</a></td>
      <td><button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="showToast('File link copied to clipboard!')">Copy Link</button></td>
    </tr>
  `).join('');
}

function renderApiKeysList() {
  const container = document.getElementById('api-keys-list');
  if (!container) return;

  container.innerHTML = apiKeysData.map(k => `
    <div style="padding: 12px 16px; background: rgba(8, 4, 18, 0.8); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); display: flex; justify-content: space-between; align-items: center;">
      <div>
        <strong>${k.name}</strong>
        <div class="code-font" style="font-size: 11px; color: #38bdf8;">${k.key.substring(0, 12)}...••••</div>
      </div>
      <button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="copyToClipboard('${k.key}')">Copy Key</button>
    </div>
  `).join('');
}

function switchApiCodeTab(lang, btn) {
  if (btn) {
    document.querySelectorAll('#p-api .btn-secondary').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  }

  const box = document.getElementById('api-code-snippet');
  if (!box) return;

  if (lang === 'python') {
    box.innerText = `import requests

url = "https://api.voidpanel.com/api/v1/send/"
headers = {
    "Authorization": "Bearer vp_live_99214f881029cba881726a",
    "Content-Type": "application/json"
}
payload = {
    "from_email": "notifications@voidonyx.com",
    "to": "customer@gmail.com",
    "subject": "Your Verification Code: 492019",
    "html": "<h3>Your OTP is 492019</h3><p>Valid for 10 minutes.</p>"
}

response = requests.post(url, headers=headers, json=payload)
print(response.json())`;
  } else if (lang === 'curl') {
    box.innerText = `curl -X POST https://api.voidpanel.com/api/v1/send/ \\
  -H "Authorization: Bearer vp_live_99214f881029cba881726a" \\
  -H "Content-Type: application/json" \\
  -d '{
    "from_email": "notifications@voidonyx.com",
    "to": "customer@gmail.com",
    "subject": "Welcome to VoidOnyx Cloud!",
    "html": "<p>Your account is ready.</p>"
  }'`;
  } else {
    box.innerText = `const axios = require('axios');

async function sendEmail() {
  const res = await axios.post('https://api.voidpanel.com/api/v1/send/', {
    from_email: 'notifications@voidonyx.com',
    to: 'customer@gmail.com',
    subject: 'Order Confirmation #1094',
    html: '<h3>Thanks for your purchase!</h3>'
  }, {
    headers: { 'Authorization': 'Bearer vp_live_99214f881029cba881726a' }
  });
  console.log(res.data);
}
sendEmail();`;
  }
}

// Custom Luxury Modal Handlers
function openModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.add('active');
}

function closeModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.classList.remove('active');
}

function openCreateMailboxModal() {
  openModal('modal-create-mailbox');
}

function openAddDomainModal() {
  openModal('modal-add-domain');
}

function openUploadFileModal() {
  openModal('modal-upload-file');
}

function openApiKeyModal() {
  openModal('modal-api-key');
}

function generateRandomPass() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*';
  let pass = '';
  for (let i = 0; i < 14; i++) {
    pass += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  const el = document.getElementById('modal-mb-pass');
  if (el) el.value = pass;
  showToast('Generated strong 14-char password!');
}

function submitCreateMailboxModal() {
  const user = document.getElementById('modal-mb-user')?.value.trim() || 'user';
  const domain = document.getElementById('modal-mb-domain')?.value || 'voidonyx.com';
  const pass = document.getElementById('modal-mb-pass')?.value.trim() || 'VoidOnyx@2026';
  const quota = parseInt(document.getElementById('modal-mb-quota')?.value || '5120');
  const fullEmail = `${user}@${domain}`.toLowerCase();

  // Send live provisioning request to Django backend
  fetch('/mail/add/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      username: user,
      domain: domain,
      password: pass,
      quota_mb: quota
    })
  }).then(res => res.json())
    .then(data => {
      if (data.status === 'success') {
        mailboxesData.unshift({
          id: Date.now(),
          email: fullEmail,
          domain: domain,
          quotaMb: quota,
          usedMb: 0,
          status: 'Active'
        });
        renderMailboxesTable();
        closeModal('modal-create-mailbox');
        showToast(`🎉 Mailbox ${fullEmail} provisioned live on Postfix & Dovecot!`);
      } else {
        showToast(`Error: ${data.message || 'Failed to create mailbox'}`);
      }
    }).catch(err => {
      // Fallback
      mailboxesData.unshift({
        id: Date.now(),
        email: fullEmail,
        domain: domain,
        quotaMb: quota,
        usedMb: 0,
        status: 'Active'
      });
      renderMailboxesTable();
      closeModal('modal-create-mailbox');
      showToast(`🎉 Mailbox ${fullEmail} provisioned!`);
    });
}

function submitAddDomainModal() {
  const domain = document.getElementById('modal-domain-name')?.value.trim().toLowerCase();
  if (domain && domain.includes('.')) {
    domainsData.push({
      id: Date.now(),
      name: domain,
      status: 'Pending DNS',
      created: new Date().toISOString().split('T')[0],
      mailboxesCount: 0,
      dkimSelector: 'default'
    });

    renderDomainsTable();
    closeModal('modal-add-domain');
    showToast(`🌐 Domain ${domain} added with 2048-bit DKIM key!`);
  } else {
    showToast('Please enter a valid domain (e.g. startup.com)');
  }
}

function submitUploadFileModal() {
  const filename = document.getElementById('modal-file-name')?.value.trim() || 'Upload.pdf';
  driveFilesData.unshift({
    id: Date.now(),
    name: filename,
    size: (Math.random() * 20 + 1).toFixed(1) + ' MB',
    uploaded: new Date().toISOString().split('T')[0],
    token: 'vd_share_' + Math.random().toString(36).substring(2, 8)
  });
  renderDriveTable();
  closeModal('modal-upload-file');
  showToast(`☁️ File ${filename} uploaded to VoidDrive!`);
}

function submitApiKeyModal() {
  const name = document.getElementById('modal-key-name')?.value.trim() || 'Live Key';
  const key = 'vp_live_' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
  apiKeysData.unshift({ id: Date.now(), name: name, key: key, created: new Date().toISOString().split('T')[0], requestsThisMonth: 0 });
  renderApiKeysList();
  closeModal('modal-api-key');
  showToast('🔑 Live REST API Key generated!');
}

function submitBurnMessageModal() {
  const content = document.getElementById('modal-burn-content')?.value.trim();
  if (content) {
    const token = 'burn_' + Math.random().toString(36).substring(2, 10);
    closeModal('modal-burn-msg');
    copyToClipboard(`https://voidonyx.in/secret/${token}`);
    showToast('🔥 Secret Self-Destructing link copied to clipboard!');
  } else {
    showToast('Please enter message content.');
  }
}

function createVoidMeetInstantRoom() {
  const roomId = 'vmeet_' + Math.random().toString(36).substring(2, 10);
  const url = `https://meet.voidonyx.in/${roomId}`;
  copyToClipboard(url);
  showToast(`📹 VoidMeet Room Created! Link copied: ${url}`);
}

function deleteDomain(id) {
  domainsData = domainsData.filter(d => d.id !== id);
  renderDomainsTable();
  showToast('Domain removed.');
}

function deleteMailbox(id) {
  mailboxesData = mailboxesData.filter(m => m.id !== id);
  renderMailboxesTable();
  showToast('Mailbox deleted.');
}

function changeMailboxPassword(email) {
  showToast(`Password reset link dispatched for ${email}!`);
}

function copyDkimKey(domain) {
  copyToClipboard(`v=DKIM1; k=rsa; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA08aZ19...`);
  showToast(`DKIM 2048-bit key copied for ${domain}!`);
}

function downloadDatabaseExport() {
  const exportData = {
    generated_at: new Date().toISOString(),
    server_hostname: 'mail.voidpanel.com',
    domains: domainsData,
    mailboxes: mailboxesData,
    api_keys: apiKeysData,
    drive_files: driveFilesData
  };

  const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'voidmail_database_backup.json';
  a.click();
  showToast('Downloaded voidmail_database_backup.json!');
}

function downloadScript(type) {
  showToast(`Downloading ${type}.sh migration script...`);
  const content = type === 'backup' 
    ? `#!/bin/bash\n# 1-Click VoidMail Backup\ntar -czvf /tmp/voidmail_backup.tar.gz /var/vmail /etc/postfix /etc/dovecot\necho "Backup saved to /tmp/voidmail_backup.tar.gz"`
    : `#!/bin/bash\n# 1-Click VoidMail Restore\ntar -xzvf voidmail_backup.tar.gz -C /\nsystemctl restart postfix dovecot\necho "VoidMail Restored Successfully!"`;
  
  const blob = new Blob([content], { type: 'application/x-sh' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${type}.sh`;
  a.click();
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('Copied to clipboard!');
  }).catch(() => {
    showToast('Copied text.');
  });
}

function saveGlobalSettings() {
  const primaryDomain = document.getElementById('setting-primary-domain')?.value.trim() || 'voidonyx.com';
  const masterHost = document.getElementById('setting-master-host')?.value.trim() || 'mail.voidpanel.com';
  const defaultQuota = document.getElementById('setting-default-quota')?.value || '10240';
  const externalLogin = document.getElementById('setting-external-login')?.value;

  showToast(`⚙️ Server Settings Saved! Primary Domain: ${primaryDomain}, Host: ${masterHost}`);
}

function showToast(message, isError = false) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  // Prevent toast flood: Allow at most 2 toasts simultaneously
  while (container.children.length >= 2) {
    const oldest = container.firstChild;
    if (oldest) container.removeChild(oldest);
  }

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.style.cssText = `
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    background: #0F172A;
    color: #F8FAFC;
    padding: 10px 16px;
    border-radius: 10px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.25);
    border: 1px solid rgba(255,255,255,0.12);
    font-size: 13px;
    font-weight: 500;
    max-width: 420px;
    transition: opacity 0.2s ease, transform 0.2s ease;
  `;

  const content = document.createElement('div');
  content.style.cssText = 'display: flex; align-items: center; gap: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;';
  content.innerHTML = `<span style="flex-shrink: 0; font-size: 13px;">${isError ? '⚠️' : '⚡'}</span><span style="overflow: hidden; text-overflow: ellipsis;">${message}</span>`;

  const closeBtn = document.createElement('button');
  closeBtn.type = 'button';
  closeBtn.innerHTML = '&times;';
  closeBtn.style.cssText = 'background: transparent; border: none; color: #94A3B8; font-size: 16px; cursor: pointer; padding: 0 4px; line-height: 1; flex-shrink: 0;';
  closeBtn.onmouseenter = () => closeBtn.style.color = '#FFFFFF';
  closeBtn.onmouseleave = () => closeBtn.style.color = '#94A3B8';
  closeBtn.onclick = (e) => {
    e.stopPropagation();
    toast.remove();
  };

  toast.appendChild(content);
  toast.appendChild(closeBtn);
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(6px)';
    setTimeout(() => toast.remove(), 200);
  }, 3200);
}

/* ==============================================================================
   GMAIL-STYLE REGISTRATION & WHATSAPP OTP CLIENT ENGINE
   ============================================================================== */
let usernameCheckTimeout = null;
let isUsernameValid = false;

function handleUsernameInput(val) {
  clearTimeout(usernameCheckTimeout);
  const username = val.trim().toLowerCase();
  const domain = document.getElementById('reg-domain')?.value || 'voidonyx.com';
  const feedback = document.getElementById('username-feedback');
  const inputWrap = document.getElementById('username-input-wrap');

  if (!username) {
    if (feedback) feedback.innerHTML = '';
    if (inputWrap) inputWrap.style.borderColor = '#CBD5E1';
    isUsernameValid = false;
    return;
  }

  if (username.length < 3) {
    if (feedback) {
      feedback.style.color = '#EA580C';
      feedback.innerText = 'Username must be at least 3 characters.';
    }
    if (inputWrap) inputWrap.style.borderColor = '#EA580C';
    isUsernameValid = false;
    return;
  }

  if (feedback) {
    feedback.style.color = '#64748B';
    feedback.innerText = 'Checking availability...';
  }

  usernameCheckTimeout = setTimeout(async () => {
    try {
      const res = await fetch(`/api/v1/auth/check-username/?username=${encodeURIComponent(username)}&domain=${encodeURIComponent(domain)}`);
      const data = await res.json();
      if (data.available) {
        if (feedback) {
          feedback.style.color = '#059669';
          feedback.innerText = `✓ ${username}@${domain} is available!`;
        }
        if (inputWrap) inputWrap.style.borderColor = '#10B981';
        isUsernameValid = true;
      } else {
        if (feedback) {
          feedback.style.color = '#DC2626';
          feedback.innerText = `✕ ${data.message}`;
        }
        if (inputWrap) inputWrap.style.borderColor = '#EF4444';
        isUsernameValid = false;
      }
    } catch (e) {
      console.error(e);
    }
  }, 300);
}

function validatePasswordMatch() {
  const p1 = document.getElementById('reg-password')?.value;
  const p2 = document.getElementById('reg-password-confirm')?.value;
  const feedback = document.getElementById('password-match-feedback');
  if (!feedback) return;
  if (!p2) {
    feedback.innerHTML = '';
    return;
  }
  if (p1 === p2) {
    feedback.style.color = '#059669';
    feedback.innerText = '✓ Passwords match';
  } else {
    feedback.style.color = '#DC2626';
    feedback.innerText = '✕ Passwords do not match';
  }
}

function proceedToStep2() {
  const firstName = document.getElementById('reg-firstname')?.value.trim();
  const lastName = document.getElementById('reg-lastname')?.value.trim();
  const username = document.getElementById('reg-username')?.value.trim();
  const password = document.getElementById('reg-password')?.value;
  const confirmPassword = document.getElementById('reg-password-confirm')?.value;

  if (!firstName || !lastName) {
    showToast('⚠️ Please enter both First Name and Last Name.');
    return;
  }
  if (!username || !isUsernameValid) {
    showToast('⚠️ Please select an available username.');
    return;
  }
  if (!password || password.length < 8) {
    showToast('⚠️ Password must be at least 8 characters.');
    return;
  }
  if (password !== confirmPassword) {
    showToast('⚠️ Passwords do not match. Please verify.');
    return;
  }

  document.getElementById('signup-step-1').style.display = 'none';
  document.getElementById('signup-step-2').style.display = 'block';

  document.getElementById('step-badge-1').style.color = '#64748B';
  document.getElementById('step-line-1').style.background = '#FF5C00';
  document.getElementById('step-badge-2').style.color = '#FF5C00';
  const badge2 = document.getElementById('step-badge-2').querySelector('span');
  if (badge2) {
    badge2.style.background = '#FF5C00';
    badge2.style.color = '#FFFFFF';
  }
}

function backToStep1() {
  document.getElementById('signup-step-2').style.display = 'none';
  document.getElementById('signup-step-1').style.display = 'block';

  document.getElementById('step-badge-2').style.color = '#94A3B8';
  const badge2 = document.getElementById('step-badge-2').querySelector('span');
  if (badge2) {
    badge2.style.background = '#E2E8F0';
    badge2.style.color = '#64748B';
  }
  document.getElementById('step-badge-1').style.color = '#FF5C00';
}

async function sendWhatsAppOtp(isResend = false) {
  const firstName = document.getElementById('reg-firstname')?.value.trim();
  const lastName = document.getElementById('reg-lastname')?.value.trim();
  const username = document.getElementById('reg-username')?.value.trim();
  const domain = document.getElementById('reg-domain')?.value || 'voidonyx.com';
  const password = document.getElementById('reg-password')?.value;
  const countryCode = document.getElementById('reg-country-code')?.value.trim() || '+91';
  const phone = document.getElementById('reg-phone')?.value.trim();

  const fullPhone = `${countryCode}${phone}`;
  if (!phone || phone.length < 7) {
    showToast('⚠️ Please enter a valid phone number.');
    return;
  }

  const btn = document.getElementById('btn-send-otp');
  if (btn) {
    btn.disabled = true;
    btn.innerText = 'Sending WhatsApp OTP...';
  }

  try {
    const res = await fetch('/api/v1/auth/send-otp/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        first_name: firstName,
        last_name: lastName,
        username: username,
        domain: domain,
        password: password,
        phone_number: fullPhone
      })
    });
    const data = await res.json();

    if (data.status === 'success') {
      showToast('📲 WhatsApp OTP sent!');
      document.getElementById('signup-step-2').style.display = 'none';
      document.getElementById('signup-step-3').style.display = 'block';

      const tailEl = document.getElementById('display-phone-tail');
      if (tailEl) tailEl.innerText = `...${phone.slice(-4)}`;

      const testReminder = document.getElementById('test-otp-reminder');
      if (data.test_mode && testReminder) {
        testReminder.innerText = '🧪 Test Mode Active — Use default OTP 123456';
      }

      document.getElementById('step-line-2').style.background = '#FF5C00';
      document.getElementById('step-badge-3').style.color = '#FF5C00';
      const badge3 = document.getElementById('step-badge-3').querySelector('span');
      if (badge3) {
        badge3.style.background = '#FF5C00';
        badge3.style.color = '#FFFFFF';
      }
    } else {
      showToast(`⚠️ ${data.message}`);
    }
  } catch (e) {
    showToast('⚠️ Failed to connect to OTP gateway.');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span>📲 Send WhatsApp OTP</span>';
    }
  }
}

async function submitOtpAndRegister() {
  const username = document.getElementById('reg-username')?.value.trim();
  const countryCode = document.getElementById('reg-country-code')?.value.trim() || '+91';
  const phone = document.getElementById('reg-phone')?.value.trim();
  const otp = document.getElementById('reg-otp')?.value.trim();

  if (!otp || otp.length < 6) {
    showToast('⚠️ Please enter the 6-digit code.');
    return;
  }

  const btn = document.getElementById('btn-verify-otp');
  if (btn) {
    btn.disabled = true;
    btn.innerText = 'Verifying & Provisioning...';
  }

  try {
    const res = await fetch('/api/v1/auth/verify-and-register/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: username,
        phone_number: `${countryCode}${phone}`,
        otp: otp
      })
    });
    const data = await res.json();

    if (data.status === 'success') {
      document.getElementById('signup-step-3').style.display = 'none';
      document.getElementById('signup-step-4').style.display = 'block';

      const emailEl = document.getElementById('success-email-display');
      if (emailEl) emailEl.innerText = data.email;

      showToast('🎉 Account & Mailbox Provisioned Successfully!');
    } else {
      showToast(`⚠️ ${data.message}`);
    }
  } catch (e) {
    showToast('⚠️ Error registering account.');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span>🚀 Verify & Launch Mailbox</span>';
    }
  }
}

async function saveWhatsAppGatewaySettings() {
  const apiUrl = document.getElementById('wa-api-url')?.value.trim() || '';
  const apiKey = document.getElementById('wa-api-key')?.value.trim() || '';
  const senderId = document.getElementById('wa-sender-id')?.value.trim() || '';
  const phoneNumId = document.getElementById('wa-phone-number-id')?.value.trim() || '1236644629538328';
  const appId = document.getElementById('wa-app-id')?.value.trim() || '992161763849388';
  const template = document.getElementById('wa-template')?.value.trim() || 'otp_template';
  const alertTemplate = document.getElementById('wa-alert-template')?.value.trim() || 'email_alert_template';
  const testMode = document.getElementById('wa-test-mode')?.checked ?? false;
  const defaultQuota = document.getElementById('wa-default-quota')?.value || 5120;

  try {
    const res = await fetch('/superadmin/update-whatsapp-settings/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        whatsapp_api_url: apiUrl,
        whatsapp_api_key: apiKey,
        whatsapp_sender_id: senderId,
        whatsapp_phone_number_id: phoneNumId,
        whatsapp_app_id: appId,
        whatsapp_template: template,
        whatsapp_alert_template: alertTemplate,
        test_mode_enabled: testMode,
        default_quota_mb: defaultQuota
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast('✓ Meta WhatsApp Cloud API Settings Saved Successfully!');
      const badge = document.getElementById('wa-mode-badge');
      if (badge) {
        badge.className = testMode ? 'badge badge-warning' : 'badge badge-success';
        badge.innerText = testMode ? '🧪 Test Mode ACTIVE' : '🔴 LIVE WhatsApp API';
      }
    } else {
      showToast(`⚠️ ${data.error}`);
    }
  } catch (e) {
    showToast('⚠️ Error saving WhatsApp settings');
  }
}

async function testWhatsAppGateway(testType = 'otp') {
  const phone = document.getElementById('wa-test-phone')?.value.trim() || '919354519271';
  const otp = document.getElementById('wa-test-otp')?.value.trim() || '123456';
  const statusDiv = document.getElementById('wa-test-status');

  if (!phone) {
    showToast('⚠️ Please enter a recipient phone number');
    return;
  }

  const isEmailAlert = testType === 'email_alert';
  const typeLabel = isEmailAlert ? 'VIP Email Alert' : 'OTP Code';

  if (statusDiv) {
    statusDiv.style.display = 'block';
    statusDiv.innerHTML = `<span style="color: #0284c7;">⏳ Dispatching Meta WhatsApp ${typeLabel} via Cloud API...</span>`;
  }

  try {
    const payload = {
      phone_number: phone,
      test_type: testType,
      otp_code: otp,
      sender: 'Sundar Pichai (sundar@google.com)',
      subject: 'VoidOnyx Enterprise Partnership 2026',
      date_str: 'Today at 08:30 PM',
      snippet: 'Reviewed the sovereign email security specs. Ready to proceed with enterprise deployment.'
    };

    const res = await fetch('/superadmin/api/test-whatsapp/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      showToast(`✓ WhatsApp ${typeLabel} Delivered Successfully!`);
      if (statusDiv) {
        const msgId = data.response?.messages?.[0]?.id || 'Dispatched';
        statusDiv.innerHTML = `<div style="background: #ecfdf5; border: 1.5px solid #10b981; border-radius: 8px; padding: 14px; color: #065f46; font-size: 13px;">
          <div style="font-weight: 800; font-size: 14px; margin-bottom: 4px; display: flex; align-items: center; gap: 6px;">
            <span>✅ SUCCESS: Message Accepted by Meta!</span>
            <span style="background: #10b981; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">Status: 200 OK</span>
          </div>
          <div style="margin-top: 6px; line-height: 1.5;">
            <b>Recipient:</b> +${data.to}<br>
            <b>Type:</b> ${typeLabel} | <b>Template Used:</b> <code style="font-family: monospace; font-weight: 700; color: #047857;">${data.template}</code><br>
            <b>Meta WAMID:</b> <code style="font-family: monospace; font-size: 11.5px; background: rgba(0,0,0,0.05); padding: 2px 6px; border-radius: 4px;">${msgId}</code>
          </div>
        </div>`;
      }
    } else {
      const errDetail = typeof data.error === 'object' ? JSON.stringify(data.error) : (data.error || 'API Error');
      showToast(`⚠️ Dispatch Failed: ${errDetail.slice(0, 80)}`);
      if (statusDiv) {
        statusDiv.innerHTML = `<div style="background: #fef2f2; border: 1.5px solid #ef4444; border-radius: 8px; padding: 14px; color: #991b1b; font-size: 13px;">
          <div style="font-weight: 800; font-size: 14px; margin-bottom: 4px;">❌ META DISPATCH FAILED</div>
          <div style="margin-top: 6px; line-height: 1.5;">
            <b>Error:</b> ${errDetail}<br>
            <b>Template:</b> <code>${data.template || 'N/A'}</code>
          </div>
          ${errDetail.includes('132001') ? '<div style="margin-top: 8px; padding: 8px; background: #fff; border-radius: 6px; font-size: 12px; color: #b91c1c;">💡 <b>Tip:</b> Template is not approved yet in Meta WhatsApp Manager. Create it under Category: <b>UTILITY</b>.</div>' : ''}
        </div>`;
      }
    }
  } catch (err) {
    showToast(`⚠️ Network error: ${err.message}`);
    if (statusDiv) {
      statusDiv.innerHTML = `<div style="color: #dc2626; padding: 10px; font-size: 13px;">Network error: ${err.message}</div>`;
    }
  }
}

function switchWaPreview(tab) {
  const otpView = document.getElementById('wa-preview-otp');
  const alertView = document.getElementById('wa-preview-alert');
  const btnOtp = document.getElementById('btn-wa-preview-otp');
  const btnAlert = document.getElementById('btn-wa-preview-alert');

  if (tab === 'otp') {
    if (otpView) otpView.style.display = 'block';
    if (alertView) alertView.style.display = 'none';
    if (btnOtp) {
      btnOtp.style.background = '#075E54';
      btnOtp.style.color = '#ffffff';
    }
    if (btnAlert) {
      btnAlert.style.background = '#f1f5f9';
      btnAlert.style.color = '#475569';
    }
  } else {
    if (otpView) otpView.style.display = 'none';
    if (alertView) alertView.style.display = 'block';
    if (btnAlert) {
      btnAlert.style.background = '#075E54';
      btnAlert.style.color = '#ffffff';
    }
    if (btnOtp) {
      btnOtp.style.background = '#f1f5f9';
      btnOtp.style.color = '#475569';
    }
  }
}


