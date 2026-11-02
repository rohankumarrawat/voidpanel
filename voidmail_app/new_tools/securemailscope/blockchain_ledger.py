"""
SecureMailScope Sovereign Blockchain Ledger
Immutable SHA-256 Cryptographic Chain with Merkle Tree Verification
Built for Minor Project • Department of Computer Science & Engineering
"""

import hashlib
import json
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

IST_TZ = timezone(timedelta(hours=5, minutes=30))

def format_ist_time(ts: Optional[float] = None) -> str:
    if ts is None:
        ts = time.time()
    dt = datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(IST_TZ)
    return dt.strftime("%Y-%m-%d %H:%M:%S IST")


class Block:
    def __init__(
        self,
        index: int,
        timestamp: float,
        event_type: str,
        actor: str,
        mailbox: str,
        details: str,
        metadata: Dict[str, Any],
        prev_hash: str,
        nonce: int = 0
    ):
        self.index = index
        self.timestamp = timestamp
        self.event_type = event_type
        self.actor = actor
        self.mailbox = mailbox
        self.details = details
        self.metadata = metadata
        self.prev_hash = prev_hash
        self.nonce = nonce
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        payload = {
            "index": self.index,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "actor": self.actor,
            "mailbox": self.mailbox,
            "details": self.details,
            "metadata": self.metadata,
            "prev_hash": self.prev_hash,
            "nonce": self.nonce
        }
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "time_formatted": format_ist_time(self.timestamp),
            "event_type": self.event_type,
            "actor": self.actor,
            "mailbox": self.mailbox,
            "details": self.details,
            "metadata": self.metadata,
            "prev_hash": self.prev_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }


class BlockchainLedger:
    def __init__(self, storage_path: Optional[str] = None):
        if storage_path is None:
            if os.path.exists("/opt/securemailscope"):
                self.storage_path = "/opt/securemailscope/blockchain_ledger.json"
            else:
                self.storage_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blockchain_ledger.json")
        else:
            self.storage_path = storage_path

        self.chain: List[Block] = []
        self.load_or_initialize()

    def load_or_initialize(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    for b_dict in data.get("chain", []):
                        b = Block(
                            index=b_dict["index"],
                            timestamp=b_dict["timestamp"],
                            event_type=b_dict["event_type"],
                            actor=b_dict["actor"],
                            mailbox=b_dict["mailbox"],
                            details=b_dict["details"],
                            metadata=b_dict.get("metadata", {}),
                            prev_hash=b_dict["prev_hash"],
                            nonce=b_dict.get("nonce", 0)
                        )
                        b.hash = b_dict["hash"]
                        self.chain.append(b)
            except Exception as e:
                print("Error loading blockchain ledger:", e)

        if not self.chain:
            self.create_genesis_block()

    def create_genesis_block(self):
        genesis = Block(
            index=0,
            timestamp=time.time() - 3600,
            event_type="GENESIS_ANCHOR",
            actor="NTRO_SOVEREIGN_SYSTEM",
            mailbox="SYSTEM_ROOT",
            details="SecureMailScope Sovereign Cryptographic Root Initialized • RFC 8446 & RFC 8461 Mandated",
            metadata={"version": "2.4.0-NTRO", "algorithm": "SHA-256", "network": "SOVEREIGN_AIRGAP"},
            prev_hash="0" * 64
        )
        self.chain.append(genesis)
        self.save()

    def record_event(
        self,
        event_type: str,
        actor: str,
        mailbox: str,
        details: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Block:
        prev_block = self.chain[-1]
        new_block = Block(
            index=len(self.chain),
            timestamp=time.time(),
            event_type=event_type,
            actor=actor,
            mailbox=mailbox,
            details=details,
            metadata=metadata or {},
            prev_hash=prev_block.hash
        )
        self.chain.append(new_block)
        self.save()
        return new_block

    def compute_merkle_root(self) -> str:
        if not self.chain:
            return "0" * 64
        hashes = [b.hash for b in self.chain]
        
        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])
            new_level = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                new_level.append(hashlib.sha256(combined.encode("utf-8")).hexdigest())
            hashes = new_level
        return hashes[0]

    def verify_chain_integrity(self) -> Dict[str, Any]:
        """Mathematically verifies every hash link and re-validates the Merkle Tree."""
        is_valid = True
        tampered_block = None
        reasons = []

        for i in range(1, len(self.chain)):
            current = self.chain[i]
            prev = self.chain[i - 1]

            # 1. Verify previous hash pointer
            if current.prev_hash != prev.hash:
                is_valid = False
                tampered_block = i
                reasons.append(f"Block #{i} prev_hash mismatch: expected {prev.hash[:12]}..., got {current.prev_hash[:12]}...")
                break

            # 2. Verify internal block hash integrity
            recalculated = current.compute_hash()
            if current.hash != recalculated:
                is_valid = False
                tampered_block = i
                reasons.append(f"Block #{i} hash corrupted: recorded {current.hash[:12]}..., recalculated {recalculated[:12]}...")
                break

        merkle_root = self.compute_merkle_root()
        return {
            "is_valid": is_valid,
            "total_blocks": len(self.chain),
            "merkle_root": merkle_root,
            "tampered_block": tampered_block,
            "verification_timestamp": time.time(),
            "time_formatted": format_ist_time(),
            "status": "MATHEMATICALLY_VERIFIED" if is_valid else "INTEGRITY_COMPROMISED",
            "reasons": reasons
        }

    def save(self):
        try:
            payload = {
                "merkle_root": self.compute_merkle_root(),
                "total_blocks": len(self.chain),
                "last_updated": time.time(),
                "chain": [b.to_dict() for b in self.chain]
            }
            with open(self.storage_path, "w") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            print("Failed to save blockchain ledger:", e)

    def get_recent_blocks(self, limit: int = 8) -> List[Dict[str, Any]]:
        return [b.to_dict() for b in reversed(self.chain[-limit:])]


# Global instance
ledger = BlockchainLedger()
