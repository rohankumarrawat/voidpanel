const EPP_STATUS_MAP = {
  // Client statuses
  clientdeleteprohibited: 'Deletion Protected: Registrar has locked domain against unauthorized deletion.',
  clienthold: 'Suspended: Registrar has temporarily paused DNS resolution for this domain.',
  clientrenewprohibited: 'Renewal Blocked: Registrar has blocked automated or manual renewals.',
  clienttransferprohibited: 'Transfer Locked: Domain is protected against unauthorized transfers to another registrar.',
  clientupdateprohibited: 'Update Protected: Domain contact/DNS details cannot be modified without unlocking.',

  // Server statuses
  serverdeleteprohibited: 'Registry Deletion Lock: Registry authority prohibits domain deletion.',
  serverhold: 'Registry Suspended: Registry has suspended DNS resolution (often for abuse/compliance).',
  serverrenewprohibited: 'Registry Renewal Block: Registry prevents domain renewal.',
  servertransferprohibited: 'Registry Transfer Lock: Registry prevents domain transfer between registrars.',
  serverupdateprohibited: 'Registry Update Lock: Registry prevents modification of domain details.',

  // Lifecycle statuses
  active: 'Active: Domain is registered, operational, and can be updated/renewed normally.',
  ok: 'OK / Normal: Domain is active with no active restrictions or special locks.',
  addperiod: 'Grace Add Period: Domain was recently registered and can be cancelled for refund.',
  'auto-renewperiod': 'Auto-Renew Grace Period: Domain expired and was automatically extended by registry.',
  redemptionperiod: 'Redemption Period: Domain expired and was deleted; owner can restore for extra fee.',
  renewperiod: 'Renewal Grace Period: Domain was explicitly renewed.',
  transferperiod: 'Transfer Grace Period: Domain was recently transferred to a new registrar.',
  pendingcreate: 'Pending Creation: Domain creation request is processing.',
  pendingdelete: 'Pending Delete: Domain is scheduled for permanent deletion and release to public.',
  pendingrenew: 'Pending Renewal: Domain renewal request is processing.',
  pendingrestore: 'Pending Restore: Request to restore domain from redemption is processing.',
  pendingtransfer: 'Pending Transfer: Transfer to new registrar is in progress.',
  inactive: 'Inactive: Domain has no active name servers or DNS records.',
};

/**
 * Translates an array of EPP status strings into detailed objects with code & plain English descriptions.
 * @param {Array<string>} statusFlags
 * @returns {Array<{ code: string, description: string }>}
 */
function parseStatusFlags(statusFlags = []) {
  if (!Array.isArray(statusFlags)) return [];

  return statusFlags.map((flag) => {
    // EPP status codes are often formatted as "clientTransferProhibited https://icann.org/epp#clientTransferProhibited"
    const cleanedCode = flag.split(' ')[0].trim();
    const lookupKey = cleanedCode.toLowerCase();
    
    const description = EPP_STATUS_MAP[lookupKey] || `Status Code ${cleanedCode}: Managed according to registry policy.`;

    return {
      code: cleanedCode,
      description,
    };
  });
}

module.exports = { parseStatusFlags, EPP_STATUS_MAP };
